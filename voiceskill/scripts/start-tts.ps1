param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8761
)

$ErrorActionPreference = "Stop"
$SkillRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $SkillRoot ".venv-tts\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    throw "TTS environment not found. Run scripts/setup.ps1 first."
}
& $Python -m uvicorn tts_server:app --app-dir $PSScriptRoot --host $HostAddress --port $Port
