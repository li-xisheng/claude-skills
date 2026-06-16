param(
    [string]$HostName = "127.0.0.1",
    [int]$Port = 0,
    [string]$Backend = "transformers",
    [string]$ModelId = "opendatalab/MinerU2.5-Pro-2605-1.2B",
    [switch]$Preload,
    [string]$Python = "D:\Miniconda3\python.exe",
    [string]$LogPath = ""
)

$ErrorActionPreference = "Continue"

function Get-FreeTcpPort {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Parse("127.0.0.1"), 0)
    try {
        $listener.Start()
        return $listener.LocalEndpoint.Port
    }
    finally {
        $listener.Stop()
    }
}

if ($Port -eq 0) {
    $Port = Get-FreeTcpPort
}
if ([string]::IsNullOrWhiteSpace($LogPath)) {
    $LogPath = Join-Path ([System.IO.Path]::GetTempPath()) "ocrskill_server_$Port.log"
}
$DisplayHost = if ($HostName -eq "0.0.0.0" -or $HostName -eq "::") { "127.0.0.1" } else { $HostName }

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

Write-Host "endpoint=http://$DisplayHost`:$Port/ocr health=http://$DisplayHost`:$Port/health log=$LogPath"
& $Python @argsList >> $LogPath 2>&1
