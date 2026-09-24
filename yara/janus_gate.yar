/*
 * Janus' Gate -- regras YARA de detecção (baseline / antes-depois)
 * Objetivo: medir quais assinaturas do payload caem conforme o script
 * é modificado (ex.: ofuscação de strings). Rode no estado atual e depois
 * de cada mudança para comparar.
 *
 * Uso direto:
 *   yara yara/janus_gate.yar janus.py
 *   yara -s yara/janus_gate.yar janus.py   (mostra a string que casou)
 */

rule Janus_Masquerade_Persistence {
    meta:
        description = "Disfarce de servico MS + auto-copia em APPDATA (copy_to_system)"
        author = "detection-test"
        reference = "janus.py"
    strings:
        $name   = "MicrosoftUpdateService"
        $runkey = "CurrentVersion\\Run"
        $msdir  = "Microsoft\\Windows"
    condition:
        all of them
}

rule Janus_Registry_Runkey {
    meta:
        description = "Chave Run do registro + winreg (add_to_registry / check_persistence)"
        author = "detection-test"
        reference = "janus.py"
    strings:
        $r1 = "CurrentVersion\\Run"
        $r2 = "HKEY_CURRENT_USER"
        $r3 = "winreg"
        $r4 = "SetValueEx"
    condition:
        2 of them
}

rule Janus_Keylogger_Pynput {
    meta:
        description = "Keylogger: pynput/Keyboard.Listener + strings keylog"
        author = "detection-test"
        reference = "janus.py"
    strings:
        $k1 = "keylog" ascii nocase
        $k2 = "keylogger" ascii nocase
        $k3 = "Keyboard.Listener"
        $k4 = "pynput"
        $k5 = "keylog_buffer"
    condition:
        2 of them
}

rule Janus_C2_Protocol {
    meta:
        description = "Protocolo C2 em texto claro"
        author = "detection-test"
        reference = "janus.py, connection.py"
    strings:
        $p1 = "[#] Client connected"
        $p2 = "[AUTO-SEND]"
        $p3 = "/persistence setup"
        $p4 = "/persistence status"
        $p5 = "/exit"
        $p6 = "/help"
        $p7 = "keylog_dumps"
    condition:
        3 of them
}

rule Janus_Behavior_Imports {
    meta:
        description = "Combinacao de imports (pega mesmo com strings ofuscadas)"
        author = "detection-test"
        reference = "janus.py"
    strings:
        $i1 = "import winreg"
        $i2 = "import shutil"
        $i3 = "from pynput import"
        $i4 = "import socket"
        $i5 = "import subprocess"
    condition:
        4 of them
}

rule Janus_Command_Dispatcher {
    meta:
        description = "Comandos do dispatcher em cmd()"
        author = "detection-test"
        reference = "janus.py"
    strings:
        $c1 = "/keylog start"
        $c2 = "/keylog stop"
        $c3 = "/keylog dump"
        $c4 = "/keylog status"
    condition:
        2 of them
}

rule Janus_Detected {
    meta:
        description = "Regra combinada: qualquer combinacao forte do payload"
        author = "detection-test"
    strings:
        $s1 = "keylog" ascii nocase
        $s2 = "MicrosoftUpdateService"
        $s3 = "CurrentVersion\\Run"
        $s4 = "Keyboard.Listener"
        $s5 = "[AUTO-SEND]"
        $s6 = "/persistence setup"
    condition:
        2 of them
}