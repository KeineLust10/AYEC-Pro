$ErrorActionPreference = "Stop"

$model = "qwen3:4b"
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

$ollamaCommand = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollamaCommand) {
    $candidate = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
    if (Test-Path -LiteralPath $candidate) {
        $ollamaPath = $candidate
    } else {
        $installer = Invoke-RestMethod -Uri "https://ollama.com/install.ps1"
        Invoke-Expression $installer
        $ollamaCommand = Get-Command ollama -ErrorAction SilentlyContinue
        if ($ollamaCommand) {
            $ollamaPath = $ollamaCommand.Source
        } else {
            $ollamaPath = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
        }
    }
} else {
    $ollamaPath = $ollamaCommand.Source
}

if (-not (Test-Path -LiteralPath $ollamaPath)) {
    throw "Ollama installation did not provide the expected executable."
}

$apiReady = $false
try {
    Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 2 | Out-Null
    $apiReady = $true
} catch {
    Start-Process -FilePath $ollamaPath -ArgumentList "serve" -WindowStyle Hidden
}

$deadline = [DateTime]::UtcNow.AddSeconds(90)
while (-not $apiReady -and [DateTime]::UtcNow -lt $deadline) {
    Start-Sleep -Seconds 2
    try {
        Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 3 | Out-Null
        $apiReady = $true
    } catch {
        $apiReady = $false
    }
}
if (-not $apiReady) {
    throw "Ollama local API did not start."
}

& $ollamaPath pull $model *> $null
if ($LASTEXITCODE -ne 0) {
    throw "The offline Turkish assistant model could not be prepared."
}

$models = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 10
if (-not ($models.models | Where-Object { $_.name -eq $model })) {
    throw "The requested offline assistant model is missing after download."
}

$asrScript = Join-Path $PSScriptRoot "prepare_offline_asr.py"
& $runtimePython $asrScript *> $null
if ($LASTEXITCODE -ne 0) {
    throw "The offline Turkish speech recognition model could not be prepared."
}

Write-Output "Offline assistant model is ready."
