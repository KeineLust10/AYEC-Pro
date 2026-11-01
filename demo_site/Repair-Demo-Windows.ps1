param(
    [Parameter(Mandatory = $true)]
    [string]$BundlePath
)

$ErrorActionPreference = "Stop"
$installRoot = "C:\AYECPro-Demo"
$taskName = "AYEC Pro Demo Web"
$stageRoot = Join-Path $env:TEMP ("AYECProDemoRepair-" + [guid]::NewGuid().ToString("N"))
$packageRoot = Join-Path $stageRoot "AYEC_Pro_Demo"
$packageApp = Join-Path $packageRoot "Web_Arayuzu"
$packageSite = Join-Path $packageRoot "demo_site"
$appRoot = Join-Path $installRoot "App"
$landingRoot = Join-Path $installRoot "Landing"
$dataRoot = Join-Path $installRoot "Data"

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this repair from an elevated PowerShell session."
}
if (-not (Test-Path -LiteralPath $BundlePath -PathType Leaf)) {
    throw "Demo bundle was not found."
}
if (-not (Test-Path -LiteralPath (Join-Path $installRoot "demo.env") -PathType Leaf)) {
    throw "Existing demo environment was not found; refusing to initialize data."
}
if (-not (Test-Path -LiteralPath (Join-Path $installRoot "Data\.ayec-demo-sandbox") -PathType Leaf)) {
    throw "Demo sandbox marker was not found; refusing to touch application data."
}

try {
    Expand-Archive -LiteralPath $BundlePath -DestinationPath $stageRoot
    foreach ($required in @(
        (Join-Path $packageApp "Main.py"),
        (Join-Path $packageApp "data\demo_template.db"),
        (Join-Path $packageApp "web\index.html"),
        (Join-Path $packageSite "index.html"),
        (Join-Path $packageSite "auto-start.js"),
        (Join-Path $packageSite "iis-landing.web.config")
    )) {
        if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
            throw "Demo bundle is missing a required app or landing file."
        }
    }
    foreach ($name in @("Start-Demo-Windows.ps1", "Cleanup-Demo-Windows.ps1")) {
        if (-not (Test-Path -LiteralPath (Join-Path $packageSite $name) -PathType Leaf)) {
            throw "Demo bundle is missing a required service script."
        }
    }

    $siteRoot = Join-Path $installRoot "demo_site"
    if (-not (Test-Path -LiteralPath $appRoot -PathType Container)) {
        throw "Existing demo application directory was not found; refusing to initialize it."
    }
    if (-not (Test-Path -LiteralPath $landingRoot -PathType Container)) {
        throw "Existing demo landing directory was not found; refusing to initialize it."
    }
    if (-not (Test-Path -LiteralPath $dataRoot -PathType Container)) {
        throw "Existing demo data directory was not found; refusing to initialize it."
    }

    if (Test-Path -LiteralPath $siteRoot -PathType Container) {
        $backupPath = $siteRoot + ".file-backup-" + (Get-Date -Format "yyyyMMddHHmmss")
        Move-Item -LiteralPath $siteRoot -Destination $backupPath
    }
    New-Item -ItemType Directory -Path $siteRoot -Force | Out-Null
    if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
        Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    }

    Copy-Item -Path (Join-Path $packageApp "*") -Destination $appRoot -Recurse -Force
    Copy-Item -LiteralPath (Join-Path $packageSite "index.html") -Destination $landingRoot -Force
    Copy-Item -LiteralPath (Join-Path $packageSite "auto-start.js") -Destination $landingRoot -Force
    Copy-Item -LiteralPath (Join-Path $packageSite "iis-landing.web.config") -Destination (Join-Path $landingRoot "web.config") -Force
    Copy-Item -LiteralPath (Join-Path $packageSite "iis-app.web.config") -Destination (Join-Path $appRoot "web\web.config") -Force
    $seedPath = Join-Path $dataRoot "demo_template.db"
    if (Test-Path -LiteralPath $seedPath -PathType Leaf) {
        $seedBackup = $seedPath + ".backup-" + (Get-Date -Format "yyyyMMddHHmmss")
        Copy-Item -LiteralPath $seedPath -Destination $seedBackup
    }
    Copy-Item -LiteralPath (Join-Path $packageApp "data\demo_template.db") -Destination $seedPath -Force

    Copy-Item -Path (Join-Path $packageSite "*") -Destination $siteRoot -Recurse -Force

    $powershell = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
    $startupScript = Join-Path $siteRoot "Start-Demo-Windows.ps1"
    $action = New-ScheduledTaskAction -Execute $powershell -Argument ("-NoProfile -File `"" + $startupScript + "`"")
    $trigger = New-ScheduledTaskTrigger -AtStartup
    $taskPrincipal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero)
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $taskPrincipal -Settings $settings -Description "Isolated AYEC Pro demo backend" -Force | Out-Null
    Start-ScheduledTask -TaskName $taskName
    Write-Output "Demo support files repaired and isolated backend task restarted. Demo data was preserved."
}
finally {
    $tempPrefix = [System.IO.Path]::GetFullPath($env:TEMP).TrimEnd('\') + '\'
    $resolvedStage = [System.IO.Path]::GetFullPath($stageRoot)
    if ($resolvedStage.StartsWith($tempPrefix, [StringComparison]::OrdinalIgnoreCase) -and
        [System.IO.Path]::GetFileName($resolvedStage).StartsWith("AYECProDemoRepair-", [StringComparison]::Ordinal)) {
        if (Test-Path -LiteralPath $resolvedStage) { Remove-Item -LiteralPath $resolvedStage -Recurse -Force }
    }
}
