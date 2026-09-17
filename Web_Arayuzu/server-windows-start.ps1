[CmdletBinding()]
param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8501,
    [string]$Database
)

$ErrorActionPreference = "Stop"
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    # Some remote and service shells do not expose a writable console handle.
}
$ProjectPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectPath ".venv\Scripts\python.exe"
if (-not $Database) { $Database = Join-Path $ProjectPath "data\ayecpro.db" }
if (-not (Test-Path -LiteralPath $Python)) { throw "Sunucu Python ortamı bulunamadı: $Python" }
if (-not (Test-Path -LiteralPath $Database)) { throw "Sunucu veritabanı bulunamadı: $Database" }

$LogDirectory = Join-Path $ProjectPath "logs"
New-Item -ItemType Directory -Path $LogDirectory -Force | Out-Null
$OutLog = Join-Path $LogDirectory "server.out.log"
$ErrorLog = Join-Path $LogDirectory "server.error.log"
$LauncherLog = Join-Path $LogDirectory "server.launcher.log"

function Write-ServerLog {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Message
    )

    $line = $Message + [Environment]::NewLine
    for ($attempt = 1; $attempt -le 5; $attempt++) {
        try {
            [System.IO.File]::AppendAllText($Path, $line, [System.Text.UTF8Encoding]::new($false))
            return
        } catch [System.IO.IOException] {
            Start-Sleep -Milliseconds (200 * $attempt)
        }
    }
    Write-Warning "Web server log is locked: $Path"
}

$existingListener = $null
try {
    $existingListener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1
} catch {
    $existingListener = $null
}
if ($existingListener) {
    Write-Host "AYEC Pro Web is already running on port $Port (PID $($existingListener.OwningProcess))."
    exit 0
}

$env:AYEC_HOST = $HostAddress
$env:AYEC_PORT = "$Port"
$env:AYEC_DB_PATH = $Database
$env:EASYOCR_MODULE_PATH = (Join-Path $ProjectPath "ocr-models\EasyOCR")
$env:USERPROFILE = (Join-Path $ProjectPath "ocr-models")
$env:AYEC_BACKUP_DIR = (Join-Path $ProjectPath "backups")
$TenantDirectoryName = "Kullan" + [char]0x0131 + "c" + [char]0x0131 + "lar"
$env:AYEC_TENANT_DIR = (Join-Path $ProjectPath $TenantDirectoryName)
$TenantDirectory = $env:AYEC_TENANT_DIR
New-Item -ItemType Directory -Path $TenantDirectory -Force | Out-Null
$env:PYTHONUTF8 = "1"
$env:PYTHONUNBUFFERED = "1"

Set-Location $ProjectPath
while ($true) {
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-ServerLog -Path $LauncherLog -Message "[$stamp] AYEC Pro Web starting: $HostAddress`:$Port"
    & $Python "Main.py" --host $HostAddress --port $Port --db $Database --tenant-dir $env:AYEC_TENANT_DIR 1>> $OutLog 2>> $ErrorLog
    $exitCode = $LASTEXITCODE
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-ServerLog -Path $ErrorLog -Message "[$stamp] Web server stopped (code: $exitCode); restarting in 5 seconds."
    Start-Sleep -Seconds 5
}
