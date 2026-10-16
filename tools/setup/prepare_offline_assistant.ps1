$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$runtimePython = Join-Path $projectRoot ".venv_active\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $runtimePython)) {
    throw "The workspace Python environment was not found. Create .venv_active before preparing the offline assistant."
}

$voicePackages = @(
    "faster-whisper==1.2.1",
    "ctranslate2==4.6.2",
    "av<19",
    "tokenizers>=0.13,<1",
    "onnxruntime==1.20.1"
)
& $runtimePython -m pip install --disable-pip-version-check --quiet --upgrade $voicePackages *> $null
if ($LASTEXITCODE -ne 0) {
    throw "The offline speech recognition runtime could not be installed."
}

$ollamaSetupScript = Join-Path $PSScriptRoot "prepare_ollama_model.ps1"
& $ollamaSetupScript

$asrScript = Join-Path $PSScriptRoot "prepare_offline_asr.py"
& $runtimePython $asrScript *> $null
if ($LASTEXITCODE -ne 0) {
    throw "The offline Turkish speech recognition model could not be prepared."
}

$ttsSetupScript = Join-Path $PSScriptRoot "install_local_tts_runtime.ps1"
& $ttsSetupScript
if (-not $?) {
    throw "The local Turkish speech synthesis runtime could not be prepared."
}

Write-Output "Offline assistant speech models are ready."
