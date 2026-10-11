[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Repair = Join-Path $Root "sync_tenant_registry.py"
$TaskName = "AYEC Pro Web"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "AYEC Python environment was not found: $Python"
}
if (-not (Test-Path -LiteralPath $Repair)) {
    throw "Tenant registry repair script was not found: $Repair"
}

Write-Host "Registering existing company databases in the live registry..." -ForegroundColor Cyan
& $Python $Repair
if ($LASTEXITCODE -ne 0) {
    throw "Tenant registry repair failed. See the error above; the database backup was retained."
}

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
if ($task.State -eq "Running") {
    Stop-ScheduledTask -TaskName $TaskName
}
Start-ScheduledTask -TaskName $TaskName

$healthy = $false
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    Start-Sleep -Seconds 1
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:8501/api/desktop/health" -TimeoutSec 2
        if ($health.ok -eq $true) {
            $healthy = $true
            break
        }
    }
    catch { }
}
if (-not $healthy) {
    throw "Registry repair completed, but the AYEC service health check failed. Review logs\server.error.log."
}

Write-Host "AYEC service is healthy. Sign in as ayecpro@gmail.com with the password from the last reset." -ForegroundColor Green
