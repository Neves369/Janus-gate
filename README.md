# 🏛️ Janus' Gate

<p align="center">
  <img width="1408" height="768" alt="janus" src="https://github.com/user-attachments/assets/c64937c5-4db3-4774-8342-6c0565fc839d" />
</p>


### *The threshold between classical infrastructure and digital persistence.*

**Janus' Gate** é uma ferramenta de estudo em segurança ofensiva focada em **Reverse Shell**, **persistência** e **keylogging**. Inspirado no deus romano Jano — o senhor dos portões, dos começos e das transições — o projeto atua como o ponto de entrada (e retorno) entre o sistema alvo e o controlador.

---

## 🛠️ Stack Técnica

| Componente | Tecnologia | Função |
| :--- | :--- | :--- |
| **Engine** | Python 3.x | Core da lógica de rede |
| **Communication** | `socket` | Abstração de baixo nível para TCP/IP |
| **Keylogger** | `pynput` | Captura e buffer de teclas no alvo |
| **Persistence** | `winreg`, `shutil` | Autostart via registro do Windows (chave Run) |
| **Interface** | Terminal interativo (`input()`) | Interação direta com o shell remoto |

---

> **obs:** O trojan foi escrito para rodar em sistemas Windows, porém a ferramenta de centro de controle
> funciona em ambientes Windows e Linux (testado em UBUNTU e Arch Linux).

---

## 📦 Dependências

```bash
pip install pynput
```

---

## 💻 Como Utilizar

### 1. Executar o Centro de Controle (Atacante)

Na sua máquina execute o arquivo `connection.py`:

**Windows:**
```bash
python connection.py
```

**Linux:**
```bash
python3 connection.py
```

### 2. Configurar o Trojan (Alvo)

Crie um arquivo `.env` na mesma pasta do `janus.py` e configure as variáveis. Todas têm valores padrão:

| Variável | Default | Descrição |
| :--- | :--- | :--- |
| `JANUS_IP` | `127.0.0.1` | Endereço do servidor C2 |
| `JANUS_PORT` | `443` | Porta do servidor C2 |
| `PROGRAM_NAME` | `MicrosoftUpdateService` | Nome usado na cópia/persistência |
| `REGISTRY_KEY_PATH` | `Software\Microsoft\Windows\CurrentVersion\Run` | Chave de autostart no registro |

Exemplo:
```ini
JANUS_IP=192.168.0.10
JANUS_PORT=443
```

Execute na máquina alvo:

**Windows:**
```bash
python janus.py
```

**Linux:**
```bash
python3 janus.py
```

---

## 🎮 Comandos do Centro de Controle

Ao conectar, o operador pode enviar os seguintes comandos:

| Comando | Descrição |
| :--- | :--- |
| `/help` | Mostra o menu de comandos |
| `/clear` | Limpa a tela |
| `/exit` | Desconecta o cliente |
| `cd <path>` | Muda o diretório de trabalho do processo alvo |

### Persistência

| Comando | Descrição |
| :--- | :--- |
| `/persistence status` | Verifica se o trojan já está persistido |
| `/persistence setup` | Configura a persistência (cópia + registro) |

### Keylogger

| Comando | Descrição |
| :--- | :--- |
| `/keylog start` | Inicia a captura de teclas |
| `/keylog stop` | Para a captura de teclas |
| `/keylog dump` | Envia as teclas capturadas |
| `/keylog status` | Mostra estado do keylogger e tamanho do buffer |

> **Auto-envio:** quando o buffer atinge 500 teclas, o trojan envia o dump automaticamente com o prefixo `[AUTO-SEND]`, e o centro de controle o salva em `keylog_dumps/` sem confirmação.

### Shell

| Comando | Descrição |
| :--- | :--- |
| Qualquer outro comando | Executado como comando de shell no alvo (stdout e stderr retornados ao operador) |

---

> **Importante:**
>
> - Não suba esse código para o VirusTotal nem plataformas semelhantes;
> - Não rode o trojan em sua própria máquina (por mais que o mesmo seja inofensivo ele possui persistência e ficará alocado nos registros do Windows consumindo memória até que você o tire de lá, e não adianta reiniciar a máquina);
> - Para testes reais, o ideal é tornar o trojan (a parte que roda no alvo) em executável do Windows (ex.: PyInstaller);
> - Esse é meu primeiro malware, aceito críticas e sugestões de melhoria;

---

⚠️ Aviso Legal

Este software foi criado exclusivamente para fins educacionais e estudos de segurança defensiva/ofensiva. O uso desta ferramenta para acessar sistemas sem autorização prévia é ilegal e antiético. Este autor não se responsabiliza pelo uso indevido do mesmo.

📄 Licença

Este projeto está sob a licença MIT.