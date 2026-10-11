[CmdletBinding()]
param(
    [string]$Root = "C:\Web_Arayuzu"
)

$ErrorActionPreference = "Stop"
$Root = [System.IO.Path]::GetFullPath($Root).TrimEnd("\")
$PackageRoot = [System.IO.Path]::GetFullPath($PSScriptRoot).TrimEnd("\")
$TaskName = "AYEC Pro Web"
$tenantName = "Kullan" + [char]0x0131 + "c" + [char]0x0131 + "lar"

function Stop-AyecService {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($task -and $task.State -eq "Running") {
        Stop-ScheduledTask -TaskName $TaskName
    }
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        $listener = Get-NetTCPConnection -LocalPort 8501 -State Listen -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if (-not $listener) { break }
        Start-Sleep -Seconds 1
    }
    $listener = Get-NetTCPConnection -LocalPort 8501 -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($listener) {
        $owner = Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)" -ErrorAction SilentlyContinue
        if ($owner.Name -ieq "python.exe" -and $owner.CommandLine -match "(?i)Main\.py") {
            Stop-Process -Id $listener.OwningProcess -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 2
        }
    }
    $listener = Get-NetTCPConnection -LocalPort 8501 -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($listener) { throw "AYEC Web did not release port 8501." }
    Start-Sleep -Seconds 2
}

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    $arguments = @(
        "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
        "`"$PSCommandPath`"", "-Root", "`"$Root`""
    )
    $process = Start-Process -FilePath "powershell.exe" -Verb RunAs -Wait -PassThru -ArgumentList $arguments
    exit $process.ExitCode
}

if ($PackageRoot.Equals($Root, [StringComparison]::OrdinalIgnoreCase) -or
    $PackageRoot.StartsWith($Root + "\", [StringComparison]::OrdinalIgnoreCase)) {
    throw "Extract the package outside C:\Web_Arayuzu before starting this installer."
}
foreach ($name in @(
    "BACKUP_BEFORE_WIPE.ps1", "CLEAN_INSTALL.ps1",
    "server-windows-install.ps1", "check_admin_login_runtime.py"
)) {
    if (-not (Test-Path -LiteralPath (Join-Path $PackageRoot $name) -PathType Leaf)) {
        throw "The extracted clean package is incomplete: $name"
    }
}
if (-not (Test-Path -LiteralPath $Root -PathType Container)) {
    throw "The existing server folder was not found: $Root"
}

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupPath = $null
$ArchivedRoot = "${Root}.pre-clean-$stamp"
$FailedRoot = "${Root}.failed-$stamp"
$BackupScript = Join-Path $PackageRoot "BACKUP_BEFORE_WIPE.ps1"
$InstallScript = Join-Path $Root "CLEAN_INSTALL.ps1"
$TenantPath = $null
$RootMoved = $false
$CopyStarted = $false
$InstallPassed = $false
$PriorArchive = $null

try {
    $PriorArchive = Get-ChildItem -LiteralPath "C:\" -Directory -Filter "Web_Arayuzu.pre-clean-*" -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -gt (Get-Date).AddHours(-12) } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    $recentBackup = Get-ChildItem -LiteralPath "C:\" -Directory -Filter "AYEC_MIGRATION_BACKUP_*" -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -gt (Get-Date).AddHours(-12) } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if ($recentBackup) {
        $candidateManifest = Join-Path $recentBackup.FullName "backup-manifest.json"
        if (Test-Path -LiteralPath $candidateManifest -PathType Leaf) {
            $manifest = Get-Content -LiteralPath $candidateManifest -Raw | ConvertFrom-Json
            if ([string]$manifest.source -eq $Root -and [int]$manifest.database_files -gt 0) {
                $BackupPath = $recentBackup.FullName
            }
        }
    }
    if (-not $BackupPath) {
        $BackupPath = "C:\AYEC_MIGRATION_BACKUP_$stamp"
        Write-Host "Creating a complete AYEC data backup..." -ForegroundColor Cyan
        & $BackupScript -Root $Root -Destination $BackupPath
    }
    else {
        Write-Host "Reusing the verified backup from the previous attempt: $BackupPath" -ForegroundColor Cyan
    }
    $TenantPath = Join-Path $BackupPath $tenantName
    if (-not (Test-Path -LiteralPath (Join-Path $BackupPath "data\ayecpro.db") -PathType Leaf)) {
        throw "The shared license registry was not found in the migration backup."
    }
    $tenantFiles = @(Get-ChildItem -LiteralPath $TenantPath -File -Filter "*.db" -ErrorAction SilentlyContinue)
    if ($tenantFiles.Count -eq 0) { throw "No tenant database was found in the migration backup." }
    Write-Host "Backup verified: $($tenantFiles.Count) tenant database(s)." -ForegroundColor Green

    if ($PriorArchive) {
        if (-not (Test-Path -LiteralPath (Join-Path $BackupPath "backup-manifest.json") -PathType Leaf)) {
            throw "A previous partial install was found, but its migration backup is incomplete."
        }
        Write-Host "Recovering files from the interrupted attempt..." -ForegroundColor Cyan
        Stop-AyecService
        & robocopy.exe $PriorArchive.FullName $Root /E /COPY:DAT /R:1 /W:2 /XJ /NFL /NDL /NP | Out-Null
        if ($LASTEXITCODE -ge 8) { throw "The previous server files could not be recovered." }
    }

    Stop-AyecService
    New-Item -ItemType Directory -Path $ArchivedRoot | Out-Null
    $RootMoved = $true
    Get-ChildItem -LiteralPath $Root -Force | ForEach-Object {
        Move-Item -LiteralPath $_.FullName -Destination $ArchivedRoot
    }
    $CopyStarted = $true
    Get-ChildItem -LiteralPath $PackageRoot -Force | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $Root -Recurse -Force
    }

    Write-Host "Restoring shared data and installing the clean server..." -ForegroundColor Cyan
    & $InstallScript -BackupPath $BackupPath
    if (-not $?) { throw "The clean server install did not complete." }
    $InstallPassed = $true

    $python = Join-Path $Root ".venv\Scripts\python.exe"
    $checkScript = Join-Path $Root "check_admin_login_runtime.py"
    $securePassword = Read-Host "Admin password check (press Enter to skip)" -AsSecureString
    if ($securePassword.Length -gt 0) {
        $passwordPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
        try {
            $plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($passwordPointer)
            $env:AYEC_ADMIN_CHECK_PASSWORD = $plainPassword
            & $python $checkScript
            $checkExit = $LASTEXITCODE
        }
        finally {
            Remove-Item Env:AYEC_ADMIN_CHECK_PASSWORD -ErrorAction SilentlyContinue
            if ($passwordPointer -ne [IntPtr]::Zero) {
                [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordPointer)
            }
            $plainPassword = $null
        }
        if ($checkExit -eq 0) {
            Write-Host "Admin login verified." -ForegroundColor Green
        }
        else {
            Write-Host "The server is healthy, but the password did not verify. The installation and backup are kept." -ForegroundColor Yellow
        }
    }
    else {
        Write-Host "Password check skipped. The healthy installation is kept." -ForegroundColor Yellow
    }
    Write-Host "Clean installation and service health verified." -ForegroundColor Green
    Write-Host "Migration backup retained at: $BackupPath" -ForegroundColor Green
}
catch {
    Write-Host "Install failed: $($_.Exception.Message)" -ForegroundColor Red
    if ($RootMoved -and (Test-Path -LiteralPath $ArchivedRoot -PathType Container)) {
        try {
            Stop-AyecService
            if ($CopyStarted) {
                if (-not (Test-Path -LiteralPath $FailedRoot -PathType Container)) {
                    New-Item -ItemType Directory -Path $FailedRoot | Out-Null
                }
                Get-ChildItem -LiteralPath $Root -Force | ForEach-Object {
                    Move-Item -LiteralPath $_.FullName -Destination $FailedRoot
                }
            }
            Get-ChildItem -LiteralPath $ArchivedRoot -Force | ForEach-Object {
                Move-Item -LiteralPath $_.FullName -Destination $Root
            }
            Remove-Item -LiteralPath $ArchivedRoot -Force
            $taskXml = Join-Path $BackupPath "AYEC-Pro-Web-task.xml"
            if (Test-Path -LiteralPath $taskXml -PathType Leaf) {
                Register-ScheduledTask -TaskName $TaskName -Xml (Get-Content -LiteralPath $taskXml -Raw) -Force | Out-Null
                Start-ScheduledTask -TaskName $TaskName
            }
            else {
                Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
            }
            Write-Host "The previous server files were restored. Failed files are kept at: $FailedRoot" -ForegroundColor Yellow
        }
        catch {
            Write-Host "Automatic rollback needs attention: $($_.Exception.Message)" -ForegroundColor Red
            Write-Host "Previous folder: $ArchivedRoot" -ForegroundColor Yellow
        }
    }
    throw
}

if ($InstallPassed -and (Test-Path -LiteralPath $ArchivedRoot -PathType Container)) {
    try {
        $expectedParent = [System.IO.Path]::GetDirectoryName($Root)
        $archiveParent = [System.IO.Path]::GetDirectoryName($ArchivedRoot)
        if (-not $expectedParent.Equals($archiveParent, [StringComparison]::OrdinalIgnoreCase) -or
            -not $ArchivedRoot.StartsWith($Root + ".pre-clean-", [StringComparison]::OrdinalIgnoreCase)) {
            throw "Archived folder path did not pass the safety check."
        }
        Remove-Item -LiteralPath $ArchivedRoot -Recurse -Force
        Write-Host "Old application files removed after successful verification." -ForegroundColor Green
    }
    catch {
        Write-Host "The verified server is running, but old files remain at: $ArchivedRoot" -ForegroundColor Yellow
    }
}

if ($InstallPassed) {
    foreach ($pattern in @("Web_Arayuzu.pre-clean-*", "Web_Arayuzu.failed-*")) {
        Get-ChildItem -LiteralPath "C:\" -Directory -Filter $pattern -ErrorAction SilentlyContinue |
            Where-Object { $_.LastWriteTime -gt (Get-Date).AddHours(-12) } |
            ForEach-Object { Remove-Item -LiteralPath $_.FullName -Recurse -Force }
    }
}
