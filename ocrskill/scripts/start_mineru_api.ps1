param(
    [string]$HostName = "127.0.0.1",
    [int]$Port = 8010,
    [string]$Backend = "transformers",
    [string]$ModelId = "opendatalab/MinerU2.5-Pro-2604-1.2B",
    [switch]$Preload,
    [string]$Python = "D:\Miniconda3\python.exe",
    [string]$LogPath = "C:\Tools\ocrskill_server.log"
)

$ErrorActionPreference = "Continue"
$argsList = @(
    "C:\Tools\ocrskill\scripts\serve_mineru_api.py",
    "--backend", $Backend,
    "--model-id", $ModelId,
    "--host", $HostName,
    "--port", "$Port"
)
if ($Preload) {
    $argsList += "--preload"
}

& $Python @argsList >> $LogPath 2>&1
