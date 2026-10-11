[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $Root

$required = @(
    "Main.py",
    "server-windows-start.ps1",
    "data\ayecpro.db",
    ".venv\Scripts\python.exe"
)
$missing = @($required | Where-Object { -not (Test-Path -LiteralPath (Join-Path $Root $_)) })
if ($missing.Count -gt 0) {
    throw "Required AYEC runtime files are missing; nothing was moved: $($missing -join ', ')"
}

$taskText = ""
$canCheckTasks = $true
try {
    $taskText = (Get-ScheduledTask | ForEach-Object {
        $_.Actions | ForEach-Object { $_.Execute + " " + $_.Arguments + " " + $_.WorkingDirectory }
    }) -join "`n"
} catch {
    $canCheckTasks = $false
    Write-Warning "Scheduled tasks could not be inspected; legacy launchers will be kept."
}

$dockerFiles = @(
    "Dockerfile",
    "docker-compose.yml",
    ".dockerignore",
    ".env.example",
    "DEPLOYMENT.md"
)
$legacyLaunchers = @(
    "AYEC_ONE_CLICK_START.cmd",
    "AYEC_ONE_CLICK_START.ps1",
    "AYEC_PRO_TEK_TIK_BASLAT.cmd",
    "AYEC_PRO_TEK_TIK_BASLAT.ps1",
    "AYEC_PRO_WEB_BASLAT.cmd",
    "baslat.ps1",
    "AYEC_4_URUN_GUNCELLE.ps1"
)

$candidates = @()
foreach ($name in $dockerFiles) {
    $path = Join-Path $Root $name
    if (Test-Path -LiteralPath $path -PathType Leaf) { $candidates += $name }
}

if ($canCheckTasks) {
    foreach ($name in $legacyLaunchers) {
        $path = Join-Path $Root $name
        if ((Test-Path -LiteralPath $path -PathType Leaf) -and $taskText.IndexOf($name, [StringComparison]::OrdinalIgnoreCase) -lt 0) {
            $candidates += $name
        }
    }
}

if ($candidates.Count -eq 0) {
    Write-Host "No safe cleanup candidates were found. Runtime and data files were not changed."
    exit 0
}

$archive = Join-Path $Root ("_archive_cleanup_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
New-Item -ItemType Directory -Path $archive | Out-Null
foreach ($name in $candidates) {
    Move-Item -LiteralPath (Join-Path $Root $name) -Destination $archive
}

Write-Host "Cleanup complete. Moved $($candidates.Count) files to: $archive" -ForegroundColor Green
Write-Host "The database, tenant data, backups, Python environment, and application folders were left in place."
