[CmdletBinding()]
param(
    [string]$Root = "C:\Web_Arayuzu",
    [string]$Destination
)

$ErrorActionPreference = "Stop"
$Root = [System.IO.Path]::GetFullPath($Root).TrimEnd("\")
if (-not (Test-Path -LiteralPath $Root -PathType Container)) {
    throw "AYEC server folder was not found: $Root"
}

if (-not $Destination) {
    $Destination = "C:\AYEC_MIGRATION_BACKUP_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
}
$Destination = [System.IO.Path]::GetFullPath($Destination).TrimEnd("\")
if ($Destination.StartsWith($Root + "\", [StringComparison]::OrdinalIgnoreCase)) {
    throw "Backup destination must be outside the folder being removed."
}
if (Test-Path -LiteralPath $Destination) {
    throw "Backup destination already exists: $Destination"
}

$tenantName = "Kullan" + [char]0x0131 + "c" + [char]0x0131 + "lar"
$directories = @(
    "data", $tenantName, "backups", "support_backups", "deleted_tenants",
    "artifacts", "plugins", "ocr-models", "logs", "config", "web\uploads"
)
$rootFiles = @(".env", "license-signing-key.pem", "official-services.json", "products.json")
$programBackupRoot = [Environment]::GetEnvironmentVariable("AYEC_PROGRAM_BACKUP_ROOT", "Machine")
if (-not $programBackupRoot) { $programBackupRoot = "C:\AYECPro Programlar" }
$downloadsRoot = [Environment]::GetEnvironmentVariable("AYEC_DOWNLOADS_DIR", "Machine")
if (-not $downloadsRoot) { $downloadsRoot = "C:\Downloads" }
$externalRoots = @(
    @{ backup_relative = "external\product_backups"; original_path = $programBackupRoot },
    @{ backup_relative = "external\downloads"; original_path = $downloadsRoot }
)
$taskName = "AYEC Pro Web"
$wasRunning = $false
$backupComplete = $false
$taskExists = $false

try {
    try {
        $task = Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
        $taskExists = $true
        $wasRunning = $task.State -eq "Running"
    }
    catch { }

    if ($wasRunning) {
        Stop-ScheduledTask -TaskName $taskName
        $stopped = $false
        for ($attempt = 0; $attempt -lt 30; $attempt++) {
            Start-Sleep -Seconds 1
            $listener = Get-NetTCPConnection -LocalPort 8501 -State Listen -ErrorAction SilentlyContinue |
                Select-Object -First 1
            if (-not $listener) { $stopped = $true; break }
        }
        if (-not $stopped) {
            throw "AYEC Web did not release port 8501; no backup was copied."
        }
    }

    New-Item -ItemType Directory -Path $Destination | Out-Null
    foreach ($relative in $directories) {
        $source = Join-Path $Root $relative
        if (-not (Test-Path -LiteralPath $source -PathType Container)) { continue }
        $target = Join-Path $Destination $relative
        New-Item -ItemType Directory -Path $target -Force | Out-Null
        & robocopy.exe $source $target /E /COPY:DAT /R:1 /W:2 /XJ /NFL /NDL /NP | Out-Null
        if ($LASTEXITCODE -ge 8) {
            throw "Folder backup failed: $relative (robocopy $LASTEXITCODE)"
        }
    }

    foreach ($name in $rootFiles) {
        $source = Join-Path $Root $name
        if (Test-Path -LiteralPath $source -PathType Leaf) {
            Copy-Item -LiteralPath $source -Destination (Join-Path $Destination $name)
        }
    }

    foreach ($item in $externalRoots) {
        $source = [System.IO.Path]::GetFullPath($item.original_path).TrimEnd("\")
        if (-not (Test-Path -LiteralPath $source -PathType Container)) { continue }
        if ($source.Equals($Root, [StringComparison]::OrdinalIgnoreCase) -or
            $source.StartsWith($Root + "\", [StringComparison]::OrdinalIgnoreCase)) {
            throw "An external data path is inside the server folder; include it in the manual backup first."
        }
        $target = Join-Path $Destination $item.backup_relative
        New-Item -ItemType Directory -Path $target -Force | Out-Null
        & robocopy.exe $source $target /E /COPY:DAT /R:1 /W:2 /XJ /NFL /NDL /NP | Out-Null
        if ($LASTEXITCODE -ge 8) {
            throw "External data backup failed: $($item.backup_relative) (robocopy $LASTEXITCODE)"
        }
    }

    if ($taskExists) {
        $xml = Export-ScheduledTask -TaskName $taskName
        [System.IO.File]::WriteAllText(
            (Join-Path $Destination "AYEC-Pro-Web-task.xml"),
            $xml,
            [System.Text.UTF8Encoding]::new($false)
        )
    }

    $databaseCount = @(Get-ChildItem -LiteralPath $Destination -Recurse -File -Filter "*.db").Count
    if (-not (Test-Path -LiteralPath (Join-Path $Destination "data\ayecpro.db"))) {
        throw "Registry database is missing from the backup."
    }
    $tenantFiles = @(Get-ChildItem -LiteralPath (Join-Path $Destination $tenantName) -File -Filter "*.db" -ErrorAction SilentlyContinue)
    if ($tenantFiles.Count -eq 0) { throw "No tenant database was found in the backup." }

    $manifest = [ordered]@{
        created_at = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
        source = $Root
        database_files = $databaseCount
        directories = $directories
        root_files = $rootFiles
        external_paths = $externalRoots
    }
    $manifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $Destination "backup-manifest.json") -Encoding UTF8
    $backupComplete = $true
    Write-Host "Backup completed: $Destination" -ForegroundColor Green
    Write-Host "Database files copied: $databaseCount"
    Write-Host "The AYEC Web task remains stopped. Copy this backup folder off the server before deleting C:\Web_Arayuzu."
}
finally {
    if (-not $backupComplete -and $wasRunning -and $taskExists) {
        Start-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    }
}
