# run_tests.ps1 — Harness de teste YARA para o Janus' Gate
#
# Uso:
#   .\yara\run_tests.ps1                       # testa o janus.py (default)
#   .\yara\run_tests.ps1 -Path dist\janus.exe  # testa o binario PyInstaller
#   .\yara\run_tests.ps1 -Path connection.py
#
# Dependencias (uma das duas):
#   - CLI yara disponivel no PATH, ou
#   - Python + modulo yara-python (pip install yara-python)
#
# Saida: por regra, imprime "[+] MATCH" com a regra que pegou o alvo,
# ou "[ ] NAO" se nao pegou. No final mostra quantas regras pegaram.

param(
    [string]$Path = "$PSScriptRoot\..\janus.py"
)

$Rules = "$PSScriptRoot\janus_gate.yar"

if (-not (Test-Path -LiteralPath $Path)) {
    Write-Error "Arquivo alvo nao encontrado: $Path"
    exit 1
}

Write-Host "==> Alvo: $Path" -ForegroundColor Cyan

# ---- Cli 'yara' disponivel? ----
$yaraCli = Get-Command yara -ErrorAction SilentlyContinue

$matchesByRule = [System.Collections.Generic.List[string]]::new()

if ($yaraCli) {
    $out = & yara -s $Rules $Path 2>$null
    foreach ($line in $out) {
        $null = $matchesByRule.Add($line)
    }
} else {
    # ---- Fallback: Python + yara-python ----
    # Guard robusto: exige o MODULO REAL (com compile). A pasta local yara/
    # poderia ser importada como namespace package e enganar o teste.
    $hasYara = python -c "import yara; print('ok' if hasattr(yara, 'compile') else 'no')" 2>$null
    if ("$hasYara" -ne "ok") {
        Write-Host "[!] Instale o yara CLI ou faca: pip install yara-python" -ForegroundColor Yellow
        exit 1
    }

    $script = @'
import sys
import yara

rules = yara.compile(filepath=sys.argv[1])
matches = rules.match(sys.argv[2])
for m in matches:
    print(m)
'@

    $out = python -c $script $Rules $Path 2>$null
    foreach ($line in $out) {
        if ($line -notmatch "^\s*$") {
            $null = $matchesByRule.Add($line)
        }
    }
}

# ---- Regras definidas no arquivo .yar ----
$definedRules = Select-String -LiteralPath $Rules -Pattern '^rule\s+(\w+)' | ForEach-Object {
    $_.Matches[0].Groups[1].Value
}

$hit = 0
foreach ($rule in $definedRules) {
    $matched = $matchesByRule | Where-Object { $_ -match "^\s*$rule(?:\b|:)" }
    if ($matched) {
        Write-Host "[+] MATCH  $rule" -ForegroundColor Green
        $hit++
    } else {
        Write-Host "[ ] NAO    $rule" -ForegroundColor DarkGray
    }
}

Write-Host ""
Write-Host "==> Resultado: $hit de $($definedRules.Count) regras pegaram o alvo" -ForegroundColor Cyan