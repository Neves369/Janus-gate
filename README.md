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
| **Communication** | `socket`, `ssl`, `cryptography` | Canal TCP cifrado: TLS + Fernet (`SecureC2Channel`) |
| **Keylogger** | `pynput` | Captura e buffer de teclas no alvo |
| **Persistence** | `winreg`, `shutil` | Autostart via registro do Windows (chave Run) |
| **Ofuscação de API** | `importlib` | Imports dinâmicos de módulos sensíveis (fora da tabela estática) |
| **Interface** | Terminal interativo (`input()`) | Interação direta com o shell remoto |

---

> **obs:** O trojan foi escrito para rodar em sistemas Windows, porém a ferramenta de centro de controle
> funciona em ambientes Windows e Linux (testado em UBUNTU e Arch Linux).

---

## 📦 Dependências

```bash
pip install pynput cryptography
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

Crie um arquivo `.env` na mesma pasta do `janus.py` e configure as variáveis. O trojan é **env-only**: se a variável existir, usa o valor dela; se não existir, tenta decriptar o padrão ofuscado embutido com `DECRYPT_KEY`; sem chave, o valor fica vazio (sem `.env` o trojan não conecta).

| Variável | Padrão (sem `.env`) | Descrição |
| :--- | :--- | :--- |
| `JANUS_IP` | `""` | Endereço do servidor C2 |
| `JANUS_PORT` | `0` | Porta do servidor C2 |
| `PROGRAM_NAME` | `""` | Nome usado na cópia/persistência |
| `REGISTRY_KEY_PATH` | `""` | Chave de autostart no registro |
| `DECRYPT_KEY` | `""` | Chave XOR dos padrões ofuscados (obrigatória para o env-only funcionar) |
| `C2_KEY` | `""` | Chave Fernet (base64) do canal C2 — a mesma nos dois lados |
| `CMD_KEY` | `""` | Chave XOR dos comandos/strings ofuscados (`COMMANDS`/`STRINGS`) |

Exemplo:
```ini
JANUS_IP=192.168.0.10
JANUS_PORT=443
DECRYPT_KEY=trocar-pela-sua-chave
C2_KEY=<chave Fernet em base64>
CMD_KEY=janus-gate-c2
```

> **Canal seguro (`SecureC2Channel`):** o tráfego C2 é cifrado com **TLS + Fernet**. Gere a chave Fernet uma única vez (`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`) e coloque em `C2_KEY` nos dois `.env`. O servidor (`connection.py`) precisa de um certificado auto-assinado (`server.crt`/`server.key`) — gere com:
> ```bash
> openssl req -x509 -newkey rsa:2048 -nodes -keyout server.key -out server.crt -days 365 -subj "/CN=janus-gate"
> ```
> O cliente ignora a validação do certificado (`CERT_NONE`).

> **Ofuscação (`encrypt/`):** os valores embutidos no `janus.py` (IP, porta, `PROGRAM_NAME`, chave de registro) estão em hex XOR gerado pela ferramenta `encrypt/`. Para customizar, gere o hex com ela e troque no código, usando a mesma `DECRYPT_KEY` no `.env`.

> **Ofuscação de imports (`importlib`):** módulos com assinatura típica de malware (`winreg`, `shutil`, `socket`, `subprocess`, `pynput.keyboard`) não são importados no topo do `janus.py`; são carregados em runtime via `importlib.import_module("...")`, mantendo os nomes como strings fora da tabela de imports estáticos — o que reduz o sinal para analisadores estáticos e EDRs.

#### Regenerar os valores ofuscados (COMMANDS / STRINGS)

Os comandos e strings do `janus.py` ficam em hex XOR (chave `CMD_KEY`). Se você trocar o `CMD_KEY` no `.env`, precisa regenerar o hex com a MESMA chave:

1. Rode a ferramenta `encrypt/`:
   ```bash
   python encrypt/main.py
   ```
2. Escolha "Encriptar", informe a string (ex.: `/keylog start`) e a nova chave.
3. Copie o hex gerado e substitua no `_COMMANDS_HEX` / `_STRINGS_HEX` do `janus.py`.

Ou gere direto em Python (mesma lógica XOR do projeto):
```python
key = "SUA_NOVA_CHAVE"
k = key.encode("utf-8")
def xor_hex(s):
    return bytes(b ^ k[i % len(k)] for i, b in enumerate(s.encode("utf-8"))).hex()

print(xor_hex("/keylog start"))   # cole o resultado no dicionário
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

## 🏗️ Estrutura do Código

### `janus.py` (trojan / agente)

| Classe | Responsabilidade |
| :--- | :--- |
| `Config` | Caminho da aplicação, `.env` e parâmetros de runtime (IP, porta, `C2_KEY`, ...) |
| `Crypto` | XOR byte a byte para encriptar/decriptar strings ofuscadas |
| `FileTransfer` | Download/upload de arquivos em base64 |
| `Keylogger` | Captura de teclas via `pynput` (buffer, start/stop/dump) |
| `Persistence` | Cópia do binário para `%APPDATA%` + entrada de autostart no registro |
| `Client` | Socket TCP + TLS, `SecureC2Channel` e dispatcher de comandos |
| `SecureC2Channel` | Ofuscação do protocolo: cifra Fernet + framing por tamanho |

### `connection.py` (centro de controle)

| Classe | Responsabilidade |
| :--- | :--- |
| `UI` | Banner, menu de ajuda e limpeza de tela |
| `KeylogStorage` | Grava os dumps de keylog em `keylog_dumps/` |
| `Server` | Listener do C2 (bind/accept), envolve a conexão em TLS+Fernet e atende o cliente |
| `SecureC2Channel` | Mesmo canal simétrico usado no agente |

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