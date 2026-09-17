[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$PackagePath,
    [string]$ApplicationPath
)

$ErrorActionPreference = "Stop"
$TaskName = "AYEC Pro Web"
$PublicUrl = "https://panel.ayecpro.com"

function Assert-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Run PowerShell as Administrator."
    }
}

function Resolve-ApplicationPath {
    param([string]$RequestedPath)

    if ($RequestedPath) {
        return (Resolve-Path -LiteralPath $RequestedPath).Path
    }

    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($task) {
        foreach ($action in $task.Actions) {
            if ($action.Arguments -match '-File\s+\"([^\"]+server-windows-start\.ps1)\"') {
                return (Split-Path -Parent $Matches[1])
            }
        }
    }

    foreach ($candidate in @("C:\Web_Arayuzu", "C:\AYEC-Pro\Web_Arayuzu")) {
        if (Test-Path -LiteralPath (Join-Path $candidate "Main.py")) {
            return $candidate
        }
    }

    throw "AYEC application directory was not found. Pass -ApplicationPath explicitly."
}

Assert-Administrator
$PackagePath = (Resolve-Path -LiteralPath $PackagePath).Path
$ApplicationPath = Resolve-ApplicationPath -RequestedPath $ApplicationPath

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$workRoot = Join-Path $env:TEMP "ayec-update-$stamp"
$payloadRoot = Join-Path $workRoot "AYECPro_Web_Server"
$backupRoot = Join-Path $ApplicationPath "backups\deployment-$stamp"

New-Item -ItemType Directory -Path $workRoot -Force | Out-Null
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
Expand-Archive -LiteralPath $PackagePath -DestinationPath $workRoot -Force
if (-not (Test-Path -LiteralPath (Join-Path $payloadRoot "Main.py"))) {
    throw "The deployment package layout is invalid."
}

$tenantDirectoryName = "Kullan" + [char]0x0131 + "c" + [char]0x0131 + "lar"
$protectedPaths = @(
    (Join-Path $ApplicationPath "data\ayecpro.db"),
    (Join-Path $ApplicationPath $tenantDirectoryName)
)
foreach ($protectedPath in $protectedPaths) {
    if (-not (Test-Path -LiteralPath $protectedPath)) {
        throw "Production data path is missing: $protectedPath"
    }
}

Write-Host "Backing up current application files to $backupRoot" -ForegroundColor Cyan
foreach ($name in @("Main.py", "requirements.txt", "server-windows-start.ps1", "configure_official_services.py", "CONFIGURE_AYEC_OFFICIAL_SERVICES.cmd")) {
    $source = Join-Path $ApplicationPath $name
    if (Test-Path -LiteralPath $source) {
        Copy-Item -LiteralPath $source -Destination $backupRoot -Force
    }
}
foreach ($name in @("src", "web")) {
    $source = Join-Path $ApplicationPath $name
    if (Test-Path -LiteralPath $source) {
        Copy-Item -LiteralPath $source -Destination $backupRoot -Recurse -Force
    }
}

Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

try {
    foreach ($name in @("Main.py", "requirements.txt", "server-windows-start.ps1", "configure_official_services.py", "CONFIGURE_AYEC_OFFICIAL_SERVICES.cmd")) {
        $payloadFile = Join-Path $payloadRoot $name
        if (Test-Path -LiteralPath $payloadFile) {
            Copy-Item -LiteralPath $payloadFile -Destination (Join-Path $ApplicationPath $name) -Force
        }
    }
    foreach ($name in @("src", "web")) {
        Copy-Item -LiteralPath (Join-Path $payloadRoot $name) -Destination $ApplicationPath -Recurse -Force
    }

    $dataPath = Join-Path $ApplicationPath "data"
    New-Item -ItemType Directory -Path $dataPath -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $payloadRoot "data\demo_template.db") -Destination (Join-Path $dataPath "demo_template.db") -Force

    [Environment]::SetEnvironmentVariable("AYEC_PUBLIC_URL", $PublicUrl, "Machine")

    $venvPython = Join-Path $ApplicationPath ".venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $venvPython)) {
        throw "The production Python environment is missing: $venvPython"
    }
    & $venvPython -m pip install --disable-pip-version-check -r (Join-Path $ApplicationPath "requirements.txt")
    if ($LASTEXITCODE -ne 0) {
        throw "Python dependency update failed."
    }

    Start-ScheduledTask -TaskName $TaskName
    $healthUrl = "http://127.0.0.1:8501/api/desktop/health"
    $healthy = $false
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        Start-Sleep -Seconds 1
        try {
            $health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 2
            if ($health.ok -eq $true) {
                $healthy = $true
                break
            }
        } catch { }
    }
    if (-not $healthy) {
        throw "AYEC health check failed after the update."
    }

    Write-Host "AYEC update completed. Production databases were preserved." -ForegroundColor Green
    Write-Host "Local health check: $healthUrl" -ForegroundColor Green
    Write-Host "Public URL setting: $PublicUrl" -ForegroundColor Green
} catch {
    Write-Host "Update failed. Restoring application files from backup." -ForegroundColor Red
    foreach ($name in @("Main.py", "requirements.txt", "server-windows-start.ps1", "configure_official_services.py", "CONFIGURE_AYEC_OFFICIAL_SERVICES.cmd")) {
        $source = Join-Path $backupRoot $name
        if (Test-Path -LiteralPath $source) {
            Copy-Item -LiteralPath $source -Destination (Join-Path $ApplicationPath $name) -Force
        }
    }
    foreach ($name in @("src", "web")) {
        $source = Join-Path $backupRoot $name
        if (Test-Path -LiteralPath $source) {
            Copy-Item -LiteralPath $source -Destination $ApplicationPath -Recurse -Force
        }
    }
    Start-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    throw
} finally {
    Remove-Item -LiteralPath $workRoot -Recurse -Force -ErrorAction SilentlyContinue
}
