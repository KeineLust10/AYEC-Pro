[CmdletBinding()]
param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8501
)

$ErrorActionPreference = "Stop"
$ProjectPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectPath
$TenantName = "Kullan" + [char]0x0131 + "c" + [char]0x0131 + "lar"
$TenantDirectory = Join-Path $ProjectPath $TenantName
$Database = Join-Path $ProjectPath "data\ayecpro.db"
$Python = Join-Path $ProjectPath ".venv\Scripts\python.exe"
$InstallScript = Join-Path $ProjectPath "server-windows-install.ps1"
$ServerScript = Join-Path $ProjectPath "server-windows-start.ps1"

if (-not (Test-Path -LiteralPath $Python)) {
    Write-Host "AYEC ilk kurulumu baslatiliyor..." -ForegroundColor Yellow
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $InstallScript -BackendPort $Port
    if ($LASTEXITCODE -ne 0) { throw "Ilk kurulum basarisiz oldu." }
}
if (-not (Test-Path -LiteralPath $Database)) { throw "Veritabani bulunamadi: $Database" }
New-Item -ItemType Directory -Path $TenantDirectory -Force | Out-Null

$env:AYEC_HOST = $HostAddress
$env:AYEC_PORT = "$Port"
$env:AYEC_DB_PATH = $Database
$env:AYEC_TENANT_DIR = $TenantDirectory
$env:AYEC_BACKUP_DIR = Join-Path $ProjectPath "backups"
$env:PYTHONUTF8 = "1"
$env:PYTHONUNBUFFERED = "1"

Write-Host "AYEC Pro Web baslatiliyor..." -ForegroundColor Cyan
$taskName = "AYEC Pro Web"
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
function Stop-OwnedServerListener {
    $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $listener) { return }
    $process = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId = $($listener.OwningProcess)" -ErrorAction SilentlyContinue
    $commandLine = [string]$process.CommandLine
    if (-not $process -or ($commandLine -notlike "*$Database*" -and $commandLine -notlike "*$ServerScript*")) {
        throw "Port $Port is used by another process. The launcher will not terminate an unrelated process."
    }
    Stop-Process -Id $listener.OwningProcess -Force -ErrorAction Stop
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        Start-Sleep -Milliseconds 500
        $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
        if (-not $listener) { return }
    }
    throw "The previous AYEC Pro server process did not release port $Port."
}
if ($task) {
    $taskArguments = [string]$task.Actions[0].Arguments
    if ($taskArguments -notmatch "-HostAddress\s+$([regex]::Escape($HostAddress))(?:\s|$)" -or $taskArguments -notmatch "-Port\s+$Port(?:\s|$)" -or $taskArguments -notlike "*$Database*") {
        throw "The AYEC Pro Web task uses different host, port, or database settings. Run server-windows-install.ps1 with the requested settings."
    }
    if ($taskArguments -notlike "*$ServerScript*") {
        throw "The AYEC Pro Web task points to another project folder. Run server-windows-install.ps1 as Administrator from this package folder."
    }
    Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
        if (-not $task -or $task.State -ne "Running") { break }
        Start-Sleep -Milliseconds 500
    }
    Stop-OwnedServerListener
    Start-ScheduledTask -TaskName $taskName
} else {
    $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($listener) { Stop-OwnedServerListener }
    $arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$ServerScript`" -HostAddress `"$HostAddress`" -Port $Port -Database `"$Database`""
    Start-Process -FilePath "powershell.exe" -ArgumentList $arguments -WindowStyle Hidden | Out-Null
}

$healthUrl = "http://127.0.0.1:$Port/api/desktop/health"
$healthy = $false
for ($attempt = 0; $attempt -lt 60; $attempt++) {
    try {
        $health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 3
        if ($health.ok -eq $true) { $healthy = $true; break }
    } catch {}
    Start-Sleep -Seconds 1
}
if (-not $healthy) {
    throw "AYEC Pro Web did not become healthy. Inspect logs\server.error.log and logs\server.launcher.log."
}
$indexPath = Join-Path $ProjectPath "web\index.html"
$indexContent = Get-Content -LiteralPath $indexPath -Raw
$appVersion = [regex]::Match($indexContent, 'app\.js\?v=([A-Za-z0-9._-]+)').Groups[1].Value
if (-not $appVersion) { throw "Web application version could not be read from web\index.html." }
try {
    $apiStatus = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/auth/status" -TimeoutSec 5
} catch {
    throw "AYEC Pro Web health check passed, but its API status could not be read. Run server-windows-install.ps1 as Administrator to update the scheduled task and IIS assets."
}
if ([string]$apiStatus.app_build_id -ne $appVersion) {
    throw "The running API version does not match this package (web: $appVersion, API: $($apiStatus.app_build_id)). Run server-windows-install.ps1 as Administrator from this package folder, then run AYEC_START.cmd."
}
Write-Host "AYEC Pro Web is running in the background." -ForegroundColor Green
