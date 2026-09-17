[CmdletBinding()]
param(
    [string]$HostAddress = $(if ($env:AYEC_HOST) { $env:AYEC_HOST } else { "127.0.0.1" }),
    [int]$Port = $(if ($env:AYEC_PORT) { [int]$env:AYEC_PORT } else { 8501 }),
    [string]$Database = $env:AYEC_DB_PATH,
    [string]$BrowserUrl
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
$ProjectPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$TenantDirectoryName = "Kullan" + [char]0x0131 + "c" + [char]0x0131 + "lar"
$env:AYEC_TENANT_DIR = if ($env:AYEC_TENANT_DIR) { $env:AYEC_TENANT_DIR } else { Join-Path $ProjectPath $TenantDirectoryName }
New-Item -ItemType Directory -Path $env:AYEC_TENANT_DIR -Force | Out-Null
$VenvPython = Join-Path $ProjectPath ".venv\Scripts\python.exe"
$VenvPythonw = Join-Path $ProjectPath ".venv\Scripts\pythonw.exe"
$BrowserHost = if ($HostAddress -in @("0.0.0.0", "::")) { "127.0.0.1" } else { $HostAddress }
$Url = "http://${BrowserHost}:$Port"
$HealthUrl = "$Url/api/desktop/health"

function Test-AyecWeb {
    try {
        $response = Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 2
        return $response.ok -eq $true
    }
    catch {
        return $false
    }
}

if (-not (Test-Path -LiteralPath $VenvPython)) {
    Write-Host "İlk kurulum yapılıyor..." -ForegroundColor Cyan
    throw "AYEC Python environment is missing. Run AYEC_PRO_TEK_TIK_BASLAT.cmd as administrator."
}

if (-not (Test-AyecWeb)) {
    $Arguments = @("Main.py", "--host", $HostAddress, "--port", "$Port")
    if ($Database) {
        $Arguments += @("--db", $Database)
    }
    $Launcher = if (Test-Path -LiteralPath $VenvPythonw) { $VenvPythonw } else { $VenvPython }
    Start-Process -FilePath $Launcher `
        -ArgumentList $Arguments `
        -WorkingDirectory $ProjectPath `
        -WindowStyle Hidden

    $ready = $false
    for ($attempt = 0; $attempt -lt 80; $attempt++) {
        Start-Sleep -Milliseconds 250
        if (Test-AyecWeb) {
            $ready = $true
            break
        }
    }

    if (-not $ready) {
        Write-Host "AYEC Pro Web başlatılamadı. Ayrıntı için şu komutu çalıştırın:" -ForegroundColor Red
        Write-Host ".\.venv\Scripts\python.exe Main.py --host $HostAddress --port $Port" -ForegroundColor Yellow
        Read-Host "Kapatmak için Enter'a basın"
        exit 1
    }
}

Write-Host "AYEC Pro Web hazır: $Url" -ForegroundColor Green
$LaunchUrl = if ($BrowserUrl) { $BrowserUrl } else { $Url }
Start-Process $LaunchUrl
