param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8762
)

$ErrorActionPreference = "Stop"
$SkillRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $SkillRoot ".venv-asr\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    throw "ASR environment not found. Run scripts/setup.ps1 first."
}
& $Python -m uvicorn asr_server:app --app-dir $PSScriptRoot --host $HostAddress --port $Port
