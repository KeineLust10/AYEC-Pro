[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $Root
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Database = Join-Path $Root "data\ayecpro.db"
$CheckScript = Join-Path $Root "check_admin_login_runtime.py"
$TenantName = "Kullan" + [char]0x0131 + "c" + [char]0x0131 + "lar"
$TenantDirectory = Join-Path $Root $TenantName

if (-not (Test-Path -LiteralPath $Python)) { throw "Python environment not found: $Python" }
if (-not (Test-Path -LiteralPath $Database)) { throw "Database not found: $Database" }
if (-not (Test-Path -LiteralPath $CheckScript)) { throw "Runtime check script not found: $CheckScript" }

Write-Host "Checks the same local authentication and Super Admin permission used by AYEC Pro Web."
Write-Host "Database: $Database"
$securePassword = Read-Host "Enter the new admin password" -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
try {
    $env:AYEC_DB_PATH = $Database
    $env:AYEC_TENANT_DIR = $TenantDirectory
    $env:AYEC_ADMIN_CHECK_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    & $Python $CheckScript
    if ($LASTEXITCODE -ne 0) { throw "Local authentication check could not complete." }
} finally {
    if ($bstr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
    Remove-Item Env:AYEC_ADMIN_CHECK_PASSWORD -ErrorAction SilentlyContinue
    Remove-Item Env:AYEC_DB_PATH -ErrorAction SilentlyContinue
    Remove-Item Env:AYEC_TENANT_DIR -ErrorAction SilentlyContinue
}
