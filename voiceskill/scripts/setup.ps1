param(
    [switch]$ReuseSystemTorch
)

$ErrorActionPreference = "Stop"
$SkillRoot = Split-Path -Parent $PSScriptRoot
$TtsVenv = Join-Path $SkillRoot ".venv-tts"
$AsrVenv = Join-Path $SkillRoot ".venv-asr"

function New-VoiceEnvironment {
    param(
        [string]$EnvironmentPath,
        [string[]]$Packages
    )

    if (-not (Test-Path -LiteralPath $EnvironmentPath)) {
        if ($ReuseSystemTorch) {
            python -m venv --system-site-packages $EnvironmentPath
        } else {
            python -m venv $EnvironmentPath
        }
    }

    $Python = Join-Path $EnvironmentPath "Scripts\python.exe"
    & $Python -m pip install --upgrade pip
    if (-not $ReuseSystemTorch) {
        & $Python -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128
    }
    & $Python -m pip install @Packages
    & $Python -c "import torch; assert torch.cuda.is_available(), 'CUDA is not available'; print(torch.__version__, torch.cuda.get_device_name(0))"
}

New-VoiceEnvironment $TtsVenv @(
    "qwen-tts==0.1.1",
    "transformers==4.57.3",
    "fastapi>=0.128,<1",
    "uvicorn[standard]>=0.41,<1",
    "python-multipart>=0.0.22",
    "soundfile>=0.13"
)

New-VoiceEnvironment $AsrVenv @(
    "qwen-asr==0.0.6",
    "transformers==4.57.6",
    "fastapi>=0.128,<1",
    "uvicorn[standard]>=0.41,<1",
    "python-multipart>=0.0.22"
)

Write-Host "Voice environments are ready."
