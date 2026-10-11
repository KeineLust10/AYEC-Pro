[CmdletBinding()]
param(
    [string]$BackupPath
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = [System.IO.Path]::GetFullPath($Root).TrimEnd("\")
$tenantName = "Kullan" + [char]0x0131 + "c" + [char]0x0131 + "lar"

if (-not $BackupPath) {
    $BackupPath = Read-Host "Path to the backup folder created before wiping C:\Web_Arayuzu"
}
if (-not (Test-Path -LiteralPath $BackupPath -PathType Container)) {
    throw "Migration backup folder was not found: $BackupPath"
}
$BackupPath = [System.IO.Path]::GetFullPath($BackupPath).TrimEnd("\")
if ($BackupPath.StartsWith($Root + "\", [StringComparison]::OrdinalIgnoreCase)) {
    throw "The migration backup must be outside the new AYEC server folder."
}
if (-not (Test-Path -LiteralPath (Join-Path $BackupPath "data\ayecpro.db") -PathType Leaf)) {
    throw "The registry database is missing from the migration backup."
}
$tenantBackup = Join-Path $BackupPath $tenantName
$tenantDatabaseFiles = @(Get-ChildItem -LiteralPath $tenantBackup -File -Filter "*.db" -ErrorAction SilentlyContinue)
if ($tenantDatabaseFiles.Count -eq 0) {
    throw "No tenant database was found in the migration backup."
}

$restoreItems = @(
    "data", $tenantName, "backups", "support_backups", "deleted_tenants",
    "artifacts", "plugins", "ocr-models", "logs", "config", "web\uploads"
)
foreach ($relative in $restoreItems) {
    $source = Join-Path $BackupPath $relative
    if (-not (Test-Path -LiteralPath $source -PathType Container)) { continue }
    $target = Join-Path $Root $relative
    New-Item -ItemType Directory -Path $target -Force | Out-Null
    & robocopy.exe $source $target /E /COPY:DAT /R:1 /W:2 /XJ /NFL /NDL /NP | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "Data restore failed: $relative (robocopy $LASTEXITCODE)" }
}

foreach ($name in @(".env", "license-signing-key.pem", "official-services.json", "products.json")) {
    $source = Join-Path $BackupPath $name
    if (Test-Path -LiteralPath $source -PathType Leaf) {
        Copy-Item -LiteralPath $source -Destination (Join-Path $Root $name) -Force
    }
}

$manifestPath = Join-Path $BackupPath "backup-manifest.json"
if (Test-Path -LiteralPath $manifestPath -PathType Leaf) {
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    foreach ($item in @($manifest.external_paths)) {
        $source = Join-Path $BackupPath ([string]$item.backup_relative)
        if (-not (Test-Path -LiteralPath $source -PathType Container)) { continue }
        $target = [System.IO.Path]::GetFullPath([string]$item.original_path).TrimEnd("\")
        if ($target.Equals($Root, [StringComparison]::OrdinalIgnoreCase) -or
            $target.StartsWith($Root + "\", [StringComparison]::OrdinalIgnoreCase)) {
            throw "An external backup target points inside the new server folder."
        }
        New-Item -ItemType Directory -Path $target -Force | Out-Null
        & robocopy.exe $source $target /E /COPY:DAT /R:1 /W:2 /XJ /NFL /NDL /NP | Out-Null
        if ($LASTEXITCODE -ge 8) { throw "External data restore failed: $($item.backup_relative)" }
    }
}

if (-not (Test-Path -LiteralPath (Join-Path $Root "data\ayecpro.db") -PathType Leaf)) {
    throw "Registry database restore could not be verified."
}
$installScript = Join-Path $Root "server-windows-install.ps1"
if (-not (Test-Path -LiteralPath $installScript -PathType Leaf)) {
    throw "Server installer is missing from the clean package."
}

Write-Host "Preserved databases and server settings were restored." -ForegroundColor Cyan
Write-Host "Installing Python dependencies, IIS proxy modules, and the AYEC Web task..." -ForegroundColor Cyan
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $installScript -BackendPort 8501
if ($LASTEXITCODE -ne 0) { throw "AYEC server installation failed. The restored data remains in place." }

$fixScript = Join-Path $Root "FIX_ADMIN_LOGIN.ps1"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $fixScript
if ($LASTEXITCODE -ne 0) { throw "AYEC service installed, but tenant/login verification needs attention." }

Write-Host "Clean AYEC Web installation completed. Sign in with the password from the last reset." -ForegroundColor Green
