[CmdletBinding()]
param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8501,
    [switch]$SkipPasswordReset
)

$ErrorActionPreference = "Stop"
$ProjectPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectPath
$TenantName = "Kullan" + [char]0x0131 + "c" + [char]0x0131 + "lar"
$TenantDirectory = Join-Path $ProjectPath $TenantName
$Database = Join-Path $ProjectPath "data\ayecpro.db"
$Python = Join-Path $ProjectPath ".venv\Scripts\python.exe"
$InstallScript = Join-Path $ProjectPath "server-windows-install.ps1"
$ResetScript = Join-Path $ProjectPath "set_super_admin_password.py"
$ServerScript = Join-Path $ProjectPath "server-windows-start.ps1"

if (-not (Test-Path -LiteralPath $Python)) {
    Write-Host "AYEC ilk kurulumu baslatiliyor..." -ForegroundColor Yellow
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $InstallScript -BackendPort $Port
    if ($LASTEXITCODE -ne 0) { throw "Ilk kurulum basarisiz oldu." }
}
if (-not (Test-Path -LiteralPath $Database)) { throw "Veritabani bulunamadi: $Database" }
New-Item -ItemType Directory -Path $TenantDirectory -Force | Out-Null

$env:AYEC_HOST = $HostAddress
$env:AYEC_PORT = "$Port"
$env:AYEC_DB_PATH = $Database
$env:AYEC_TENANT_DIR = $TenantDirectory
$env:AYEC_BACKUP_DIR = Join-Path $ProjectPath "backups"
$env:PYTHONUTF8 = "1"
$env:PYTHONUNBUFFERED = "1"

if (-not $SkipPasswordReset) {
    $securePassword = Read-Host "AYEC Admin password for ayecpro@gmail.com" -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
    try {
        $env:AYEC_ADMIN_EMAIL = "ayecpro@gmail.com"
        $env:AYEC_ADMIN_RESET_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
        & $Python $ResetScript
        if ($LASTEXITCODE -ne 0) { throw "Admin password reset failed." }
    }
    finally {
        if ($bstr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
        Remove-Item Env:AYEC_ADMIN_RESET_PASSWORD -ErrorAction SilentlyContinue
    }
}

Write-Host "AYEC Pro Web baslatiliyor..." -ForegroundColor Cyan
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $ServerScript -HostAddress $HostAddress -Port $Port -Database $Database
exit $LASTEXITCODE
