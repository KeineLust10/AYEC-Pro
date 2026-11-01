param(
    [Parameter(Mandatory = $true)]
    [string]$BundlePath,
    [Parameter(Mandatory = $true)]
    [string]$PythonPath = ""
)

$ErrorActionPreference = "Stop"
$installRoot = "C:\AYECPro-Demo"
$stageRoot = Join-Path $env:TEMP ("AYECProDemo-" + [guid]::NewGuid().ToString("N"))

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this installer from an elevated PowerShell session."
}
if (-not (Test-Path -LiteralPath $BundlePath -PathType Leaf)) { throw "Demo bundle was not found." }
if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) { throw "The selected Python executable was not found." }
if (Test-Path -LiteralPath $installRoot) { throw "C:\AYECPro-Demo already exists; refusing to overwrite it." }
foreach ($taskName in @("AYEC Pro Demo Web", "AYEC Pro Demo Cleanup")) {
    if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
        throw ("Scheduled task already exists; refusing to replace it: " + $taskName)
    }
}

try {
    Expand-Archive -LiteralPath $BundlePath -DestinationPath $stageRoot
    $packageRoot = Join-Path $stageRoot "AYEC_Pro_Demo"
    $packageApp = Join-Path $packageRoot "Web_Arayuzu"
    $packageSite = Join-Path $packageRoot "demo_site"
    foreach ($required in @(
        (Join-Path $packageApp "Main.py"),
        (Join-Path $packageApp "data\demo_template.db"),
        (Join-Path $packageSite "index.html"),
        (Join-Path $packageSite "reset_demo_sessions.py")
    )) {
        if (-not (Test-Path -LiteralPath $required -PathType Leaf)) { throw "Bundle is incomplete." }
    }

    $appRoot = Join-Path $installRoot "App"
    $landingRoot = Join-Path $installRoot "Landing"
    $dataRoot = Join-Path $installRoot "Data"
    New-Item -ItemType Directory -Path $appRoot,$landingRoot,$dataRoot -Force | Out-Null
    $demoSiteRoot = Join-Path $installRoot "demo_site"
    New-Item -ItemType Directory -Path $demoSiteRoot -Force | Out-Null
    Copy-Item -Path (Join-Path $packageApp "*") -Destination $appRoot -Recurse -Force
    Copy-Item -LiteralPath (Join-Path $packageSite "index.html") -Destination $landingRoot
    Copy-Item -LiteralPath (Join-Path $packageSite "iis-landing.web.config") -Destination (Join-Path $landingRoot "web.config")
    Copy-Item -LiteralPath (Join-Path $packageSite "iis-app.web.config") -Destination (Join-Path $appRoot "web\web.config")
    Copy-Item -LiteralPath (Join-Path $packageSite "demo.windows.env.example") -Destination (Join-Path $installRoot "demo.env")
    Copy-Item -LiteralPath (Join-Path $packageApp "data\demo_template.db") -Destination (Join-Path $dataRoot "demo_template.db")
    Copy-Item -Path (Join-Path $packageSite "*") -Destination $demoSiteRoot -Recurse -Force

    foreach ($folder in @("tenants", "backups", "support-backups", "program-backups", "downloads", "logs")) {
        New-Item -ItemType Directory -Path (Join-Path $dataRoot $folder) -Force | Out-Null
    }
    New-Item -ItemType File -Path (Join-Path $dataRoot ".ayec-demo-sandbox") -Force | Out-Null
    Add-Content -LiteralPath (Join-Path $installRoot "demo.env") -Value ("AYEC_DEMO_PYTHON=" + $PythonPath)
    $secretBytes = New-Object byte[] 32
    $random = [Security.Cryptography.RandomNumberGenerator]::Create()
    $random.GetBytes($secretBytes)
    $trackingSecret = [Convert]::ToBase64String($secretBytes)
    $random.Dispose()
    Add-Content -LiteralPath (Join-Path $installRoot "demo.env") -Value ("AYEC_TRACKING_SECRET=" + $trackingSecret)

    $startupScript = Join-Path $installRoot "demo_site\Start-Demo-Windows.ps1"
    $cleanupScript = Join-Path $installRoot "demo_site\Cleanup-Demo-Windows.ps1"
    $powershell = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
    $startupAction = New-ScheduledTaskAction -Execute $powershell -Argument ("-NoProfile -File `"" + $startupScript + "`"")
    $startupTrigger = New-ScheduledTaskTrigger -AtStartup
    $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
    Register-ScheduledTask -TaskName "AYEC Pro Demo Web" -Action $startupAction -Trigger $startupTrigger -Principal $principal -Description "Isolated AYEC Pro demo backend" | Out-Null

    $cleanupAction = New-ScheduledTaskAction -Execute $powershell -Argument ("-NoProfile -File `"" + $cleanupScript + "`"")
    $cleanupTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date).Date.AddMinutes(15) -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Days 3650)
    Register-ScheduledTask -TaskName "AYEC Pro Demo Cleanup" -Action $cleanupAction -Trigger $cleanupTrigger -Principal $principal -Description "Remove expired isolated AYEC Pro demo workspaces" | Out-Null
    Start-ScheduledTask -TaskName "AYEC Pro Demo Web"
    Write-Output "Installed isolated demo files and scheduled tasks. Configure separate IIS bindings and HTTPS before changing DNS."
}
finally {
    $tempPrefix = [System.IO.Path]::GetFullPath($env:TEMP).TrimEnd('\') + '\'
    $resolvedStage = [System.IO.Path]::GetFullPath($stageRoot)
    if ($resolvedStage.StartsWith($tempPrefix, [StringComparison]::OrdinalIgnoreCase) -and
        [System.IO.Path]::GetFileName($resolvedStage).StartsWith("AYECProDemo-", [StringComparison]::Ordinal)) {
        if (Test-Path -LiteralPath $resolvedStage) { Remove-Item -LiteralPath $resolvedStage -Recurse -Force }
    }
}
