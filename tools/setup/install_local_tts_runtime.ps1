$ErrorActionPreference = "Stop"

$python = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    $pythonCommand = Get-Command py -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        $python = "py"
    } else {
        throw "Python 3.12 is required for the local Turkish speech runtime."
    }
}

$runtime = Join-Path $env:LOCALAPPDATA "AYEC Pro\TTSRuntime"
$runtimePython = Join-Path $runtime "Scripts\python.exe"
$requirements = Resolve-Path (Join-Path $PSScriptRoot "..\..\requirements-tts.txt")

if (-not (Test-Path -LiteralPath $runtimePython)) {
    if ($python -eq "py") {
        & py -3.12 -m venv --system-site-packages $runtime
    } else {
        & $python -m venv --system-site-packages $runtime
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create the isolated TTS runtime."
    }
}

& $runtimePython -m pip install -r $requirements.Path --disable-pip-version-check --quiet
if ($LASTEXITCODE -ne 0) {
    throw "Could not install the local EMA Turkish TTS runtime."
}

$env:HF_HUB_DISABLE_PROGRESS_BARS = "1"
$env:HF_HUB_DISABLE_TELEMETRY = "1"
& $runtimePython -c "from ema_lightning import EMA; EMA(device='cpu')" *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Could not download and verify the local Turkish TTS model weights."
}

Write-Output "Local EMA Turkish TTS runtime and model are ready for offline use."
