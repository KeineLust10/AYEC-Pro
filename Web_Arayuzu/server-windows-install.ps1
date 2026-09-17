[CmdletBinding()]
param(
    [string]$PublicIp = "85.117.239.60",
    [int]$BackendPort = 8501,
    [string]$Python,
    [switch]$SkipIisModuleInstall
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
$ProjectPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$TaskName = "AYEC Pro Web"

function Assert-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Bu betiği Yönetici olarak açılmış PowerShell penceresinde çalıştırın."
    }
}

function Install-MsiIfMissing {
    param(
        [string]$Name,
        [scriptblock]$Installed,
        [string]$Url,
        [string]$FileName
    )
    if (& $Installed) {
        Write-Host "$Name zaten kurulu." -ForegroundColor DarkGreen
        return
    }
    if ($SkipIisModuleInstall) { throw "$Name kurulu değil ve -SkipIisModuleInstall seçildi." }
    $target = Join-Path $env:TEMP $FileName
    Write-Host "$Name Microsoft'tan indiriliyor..." -ForegroundColor Cyan
    Invoke-WebRequest -Uri $Url -OutFile $target -UseBasicParsing
    $process = Start-Process msiexec.exe -ArgumentList @("/i", "`"$target`"", "/qn", "/norestart") -Wait -PassThru
    if ($process.ExitCode -notin @(0, 1641, 3010)) { throw "$Name kurulamadı (msiexec: $($process.ExitCode))." }
}

function Resolve-OrInstallPython {
    param([string]$RequestedPython)
    if ($RequestedPython) {
        if (-not (Test-Path -LiteralPath $RequestedPython)) { throw "Python bulunamadı: $RequestedPython" }
        return (Resolve-Path -LiteralPath $RequestedPython).Path
    }
    foreach ($candidate in @("python.exe", "python")) {
        $command = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($command) {
            try {
                $version = (& $command.Source -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null).Trim()
                if ([version]$version -ge [version]"3.11" -and [version]$version -lt [version]"3.13") {
                    return $command.Source
                }
            }
            catch {
                # Microsoft Store aliases and broken PATH entries are ignored;
                # the verified Python 3.12 installer below remains the fallback.
            }
        }
    }
    $installRoot = Join-Path $env:ProgramFiles "Python312"
    $installedPython = Join-Path $installRoot "python.exe"
    if (-not (Test-Path -LiteralPath $installedPython)) {
        $installer = Join-Path $env:TEMP "python-3.12.10-amd64.exe"
        Write-Host "Python 3.12.10 indiriliyor ve kuruluyor..." -ForegroundColor Cyan
        Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe" -OutFile $installer -UseBasicParsing
        $arguments = @(
            "/quiet", "InstallAllUsers=1", "PrependPath=1", "Include_launcher=0",
            "Include_test=0", "Include_doc=0", "TargetDir=$installRoot"
        )
        $process = Start-Process -FilePath $installer -ArgumentList $arguments -Wait -PassThru -WindowStyle Hidden
        if ($process.ExitCode -ne 0) { throw "Python kurulamadı (çıkış kodu: $($process.ExitCode))." }
    }
    if (-not (Test-Path -LiteralPath $installedPython)) { throw "Python kurulumu doğrulanamadı: $installedPython" }
    return $installedPython
}

Assert-Administrator

Import-Module ServerManager
foreach ($feature in @("Web-Server", "Web-Mgmt-Tools")) {
    if (-not (Get-WindowsFeature $feature).Installed) {
        Install-WindowsFeature $feature -IncludeManagementTools | Out-Null
    }
}
$AppCmd = Join-Path $env:WINDIR "System32\inetsrv\appcmd.exe"
Install-MsiIfMissing -Name "IIS URL Rewrite 2" `
    -Installed { (& $AppCmd list modules) -match "RewriteModule" } `
    -Url "https://download.microsoft.com/download/1/2/8/128E2E22-C1B9-44A4-BE2A-5859ED1D4592/rewrite_amd64_en-US.msi" `
    -FileName "rewrite_amd64_en-US.msi"
Install-MsiIfMissing -Name "IIS Application Request Routing 3" `
    -Installed { Test-Path -LiteralPath (Join-Path $env:ProgramFiles "IIS\Application Request Routing\requestRouter.dll") } `
    -Url "https://go.microsoft.com/fwlink/?LinkID=615136" `
    -FileName "requestRouter_amd64.msi"

Write-Host "Python ve AYEC çalışma zamanı kuruluyor..." -ForegroundColor Cyan
$Python = Resolve-OrInstallPython -RequestedPython $Python
$VenvPath = Join-Path $ProjectPath ".venv"
$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $VenvPython)) {
    & $Python -m venv $VenvPath
    if ($LASTEXITCODE -ne 0) { throw "AYEC Python environment could not be created." }
}
& $VenvPython -m pip install --disable-pip-version-check -r (Join-Path $ProjectPath "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "AYEC Python çalışma zamanı kurulamadı." }

$Database = Join-Path $ProjectPath "data\ayecpro.db"
if (-not (Test-Path -LiteralPath $Database)) {
    throw "data\ayecpro.db is missing. Web interface directory is incomplete."
}

Write-Host "SQLite operasyon schema kontrol ediliyor; veriler korunur..." -ForegroundColor Cyan
& $Python (Join-Path $ProjectPath "tools\repair_database.py") --database $Database
if ($LASTEXITCODE -ne 0) { throw "SQLite schema repair failed." }

$StartScript = Join-Path $ProjectPath "server-windows-start.ps1"
$actionArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$StartScript`" -HostAddress 127.0.0.1 -Port $BackendPort -Database `"$Database`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $actionArgs -WorkingDirectory $ProjectPath
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero)
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null

Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
Start-ScheduledTask -TaskName $TaskName
$healthUrl = "http://127.0.0.1:$BackendPort/api/desktop/health"
$healthy = $false
for ($attempt = 0; $attempt -lt 90; $attempt++) {
    Start-Sleep -Seconds 1
    try {
        $health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 2
        if ($health.ok -eq $true) { $healthy = $true; break }
    }
    catch { }
}
if (-not $healthy) {
    throw "AYEC arka uç servisi başlatılamadı. logs\server.error.log dosyasını kontrol edin."
}

& $AppCmd set config /section:system.webServer/proxy /enabled:"True" /preserveHostHeader:"True" /reverseRewriteHostInResponseHeaders:"False" /commit:apphost | Out-Null

Import-Module WebAdministration
$site = Get-Website -Name "Default Web Site" -ErrorAction SilentlyContinue
if (-not $site) {
    $iisRoot = Join-Path $env:SystemDrive "inetpub\wwwroot"
    New-Item -ItemType Directory -Path $iisRoot -Force | Out-Null
    New-Website -Name "Default Web Site" -Port 80 -IPAddress "*" -PhysicalPath $iisRoot | Out-Null
    $site = Get-Website -Name "Default Web Site"
}
$siteRoot = [Environment]::ExpandEnvironmentVariables($site.physicalPath)
New-Item -ItemType Directory -Path $siteRoot -Force | Out-Null
$webConfig = Join-Path $siteRoot "web.config"
if (Test-Path -LiteralPath $webConfig) {
    Copy-Item -LiteralPath $webConfig -Destination "$webConfig.before-ayec-$(Get-Date -Format yyyyMMddHHmmss).bak" -Force
}
$template = Get-Content -LiteralPath (Join-Path $ProjectPath "iis\web.config") -Raw
$template.Replace("__AYEC_BACKEND_PORT__", "$BackendPort") | Set-Content -LiteralPath $webConfig -Encoding UTF8

& $AppCmd set config "Default Web Site" /section:system.webServer/security/authentication/anonymousAuthentication /enabled:"True" /commit:apphost | Out-Null
& $AppCmd set config "Default Web Site" /section:system.webServer/security/authentication/windowsAuthentication /enabled:"False" /commit:apphost | Out-Null

if (-not (Get-NetFirewallRule -DisplayName "AYEC Pro Web HTTP" -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName "AYEC Pro Web HTTP" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow | Out-Null
}
Start-Website -Name "Default Web Site"
& iisreset.exe /restart | Out-Null

Write-Host ""
Write-Host "AYEC Pro Web sunucu kurulumu tamamlandı." -ForegroundColor Green
Write-Host "Adres: http://$PublicIp" -ForegroundColor Green
Write-Host "Arka uç: $healthUrl (yalnızca sunucu içinden)" -ForegroundColor DarkGray
Write-Host "Erişim: AYEC Pro kurulum sihirbazı ve uygulama giriş ekranıyla korumalı" -ForegroundColor Green
