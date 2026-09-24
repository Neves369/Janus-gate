# Testes com YARA

Conjunto de regras YARA para **medir** o quanto o payload (`janus.py` /
`connection.py`) é detectável por assinatura estática — e como isso muda
conforme o código é modificado.

## Como rodar

### Opção A — CLI `yara` (Linux/WSL ou instalado)

```bash
yara yara/janus_gate.yar janus.py          # so o nome das regras que pegaram
yara -s yara/janus_gate.yar janus.py       # + mostra qual string casou
```

### Opção B — script PowerShell (Windows)

```powershell
# usa o CLI yara se existir; senao, precisa de yara-python
pip install yara-python
.\yara\run_tests.ps1                       # alvo: janus.py
.\yara\run_tests.ps1 -Path dist\janus.exe  # alvo: exe gerado pelo PyInstaller
.\yara\run_tests.ps1 -Path connection.py
```

Se a execução de scripts estiver bloqueada (erro `PSSecurityException`), rode
por processo com:

```powershell
powershell -ExecutionPolicy Bypass -NoProfile -File .\yara\run_tests.ps1
```

O script imprime por regra `[+] MATCH` ou `[ ] NAO` e o total no final.

## Regras

| Regra | O que pega | Onde no código |
| :--- | :--- | :--- |
| `Janus_Masquerade_Persistence` | Nome falso de serviço MS + pasta AppData\Microsoft + chave Run | `copy_to_system`, `PROGRAM_NAME` |
| `Janus_Registry_Runkey` | Caminho `CurrentVersion\Run` + uso de `winreg` | `add_to_registry` / `check_persistence` |
| `Janus_Keylogger_Pynput` | Strings `keylog` + `pynput` / `Keyboard.Listener` | `start_keylogger`, `on_press` |
| `Janus_C2_Protocol` | Protocolo em texto claro (`[#] Client connected`, `[AUTO-SEND]`, comandos `/`) | `connect`, `listen`, `cmd` |
| `Janus_Behavior_Imports` | Combinação de imports (`winreg`, `shutil`, `pynput`, `socket`, `subprocess`) | cabeçalho do `janus.py` |
| `Janus_Command_Dispatcher` | Comandos `/keylog ...` literais no dispatcher | `cmd()` |
| `Janus_Detected` | Combinada: 2+ sinais fortes juntos | — |

> As regras miram o **implant** (`janus.py`). Rodar em `connection.py` (server)
> é opcional e naturalmente bate em menos regras — ex.: 4/7 (keylogger,
> protocolo, dispatcher e combinada).

## Como interpretar (antes/depois)

1. Rode no estado atual → anote quais regras pegaram (baseline = 7/7).
2. Modifique uma categoria (ex.: ofusque as strings `keylog`) → re- rode.
3. Veja **qual regra parou de pegar**. Se `Janus_Behavior_Imports` continuar
   pegando, é por causa dos `import`/nomes de módulo — ofuscação de string
   não os afeta.
4. Ao final, meça num binário real:
   ```bash
   pyinstaller --onefile --noconsole janus.py
   yara -s yara/janus_gate.yar dist\janus.exe
   ```

## Caveat importante

YARA varre **bytes brutos** do arquivo. No `.py` em texto puro, comentários e
`print` também contêm as strings (ex.: `[AUTO-SEND]` aparece em comentário),
o que **infla os matches**. Para uma medição justa do que um AV veria, teste
sobre o **exe** gerado pelo PyInstaller, não só sobre o código-fonte.