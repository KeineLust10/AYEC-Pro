$ErrorActionPreference = "Stop"

$model = "qwen3:4b"
$ollamaCommand = Get-Command ollama -ErrorAction SilentlyContinue
if ($ollamaCommand) {
    $ollamaPath = $ollamaCommand.Source
} else {
    $ollamaPath = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
}

if (-not (Test-Path -LiteralPath $ollamaPath)) {
    $installerScript = Invoke-RestMethod -Uri "https://ollama.com/install.ps1"
    Invoke-Expression $installerScript
    $ollamaCommand = Get-Command ollama -ErrorAction SilentlyContinue
    if ($ollamaCommand) {
        $ollamaPath = $ollamaCommand.Source
    }
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
