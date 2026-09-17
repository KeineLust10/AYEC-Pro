param(
    [string]$ProjectPath = "C:\Users\yedek\Desktop\yapay zeka\AYEC Pro",
    [string]$Model = "qwen3-coder:30b"
)

$ErrorActionPreference = "Stop"

$ToolsRoot = Split-Path -Parent $PSScriptRoot
$WorkspaceRoot = Split-Path -Parent $ToolsRoot
$PythonExe = Join-Path $WorkspaceRoot ".venv_active\Scripts\python.exe"
$ProxyScript = Join-Path $PSScriptRoot "anthropic_proxy.py"
$ClaudeExe = "C:\Users\yedek\AppData\Roaming\npm\claude.cmd"
$OllamaExe = "C:\Users\yedek\AppData\Local\Programs\Ollama\ollama.exe"
$ProxyPort = 4000
$OllamaPort = 11434

function Test-OllamaReady {
    try {
        & $OllamaExe list | Out-Null
        return $true
    } catch {
        return $false
    }
}

function Test-PortOpen {
    param([int]$Port)
    $result = Test-NetConnection -ComputerName 127.0.0.1 -Port $Port -WarningAction SilentlyContinue
    return [bool]$result.TcpTestSucceeded
}

function Wait-Port {
    param(
        [int]$Port,
        [int]$TimeoutSeconds = 45,
        [string]$Label
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-PortOpen -Port $Port) {
            return
        }
        Start-Sleep -Seconds 1
    }

    throw "$Label baslatilamadi. Port $Port acilmadi."
}

if (-not (Test-Path -LiteralPath $ProjectPath)) {
    throw "Proje yolu bulunamadi: $ProjectPath"
}

if (-not (Test-Path -LiteralPath $PythonExe)) {
    throw "Python bulunamadi: $PythonExe"
}

if (-not (Test-Path -LiteralPath $ProxyScript)) {
    throw "Proxy script bulunamadi: $ProxyScript"
}

if (-not (Test-Path -LiteralPath $ClaudeExe)) {
    throw "Claude Code bulunamadi: $ClaudeExe"
}

if (-not (Test-Path -LiteralPath $OllamaExe)) {
    throw "Ollama bulunamadi: $OllamaExe"
}

if (-not (Test-PortOpen -Port $OllamaPort)) {
    Write-Host "Ollama sunucusu baslatiliyor..."
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c start ""Ollama Serve"" /min ""$OllamaExe"" serve" | Out-Null
    Wait-Port -Port $OllamaPort -Label "Ollama"
}

$ollamaDeadline = (Get-Date).AddSeconds(30)
while ((Get-Date) -lt $ollamaDeadline) {
    if (Test-OllamaReady) {
        break
    }
    Start-Sleep -Seconds 1
}

if (-not (Test-OllamaReady)) {
    throw "Ollama portu acik ama servis komutlara cevap vermiyor."
}

if (-not (Test-PortOpen -Port $ProxyPort)) {
    Write-Host "Anthropic proxy baslatiliyor..."
    $proxyCommand = "`$env:LOCAL_OLLAMA_MODEL='$Model'; & '$PythonExe' '$ProxyScript'"
    Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $proxyCommand | Out-Null
    Wait-Port -Port $ProxyPort -Label "Anthropic proxy"
}

Set-Location -LiteralPath $ProjectPath
$env:LOCAL_OLLAMA_MODEL = $Model
$env:ANTHROPIC_BASE_URL = "http://127.0.0.1:$ProxyPort"
$env:ANTHROPIC_API_KEY = "sk-local"

Write-Host ""
Write-Host "Yerel Claude oturumu aciliyor..."
Write-Host "Proje: $ProjectPath"
Write-Host "Model: $Model"
Write-Host "Proxy: $($env:ANTHROPIC_BASE_URL)"
Write-Host ""

& $ClaudeExe --bare --model claude-sonnet-4-6 --permission-mode acceptEdits
