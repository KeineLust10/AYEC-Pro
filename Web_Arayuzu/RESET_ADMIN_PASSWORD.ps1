[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$ScriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$RuntimeRoot = $null
$SearchPath = $ScriptDirectory
for ($level = 0; $level -lt 6 -and $SearchPath; $level++) {
    if ((Test-Path -LiteralPath (Join-Path $SearchPath "Main.py")) -and
        (Test-Path -LiteralPath (Join-Path $SearchPath "data\ayecpro.db"))) {
        $RuntimeRoot = $SearchPath
        break
    }
    $parent = Split-Path -Parent $SearchPath
    if ($parent -eq $SearchPath) { break }
    $SearchPath = $parent
}
if (-not $RuntimeRoot) {
    throw "Could not find the live AYEC folder containing Main.py and data\ayecpro.db."
}

$ResetScript = Join-Path $ScriptDirectory "set_super_admin_password.py"
if (-not (Test-Path -LiteralPath $ResetScript)) {
    $ResetScript = Join-Path $RuntimeRoot "set_super_admin_password.py"
}
if (-not (Test-Path -LiteralPath $ResetScript)) {
    throw "set_super_admin_password.py was not found beside this script or in the live AYEC folder."
}
$Database = Join-Path $RuntimeRoot "data\ayecpro.db"
$TenantDirectoryName = "Kullan" + [char]0x0131 + "c" + [char]0x0131 + "lar"
$TenantDirectory = Join-Path $RuntimeRoot $TenantDirectoryName
$Python = Join-Path $RuntimeRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Python)) {
    $command = Get-Command python.exe, python -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($command) { $Python = $command.Source }
}
if (-not (Test-Path -LiteralPath $Python) -and -not (Get-Command $Python -ErrorAction SilentlyContinue)) {
    throw "Python was not found. Run the AYEC server installer first."
}

Write-Host "AYEC folder: $RuntimeRoot"
Write-Host "Database: $Database"
$securePassword = Read-Host "New AYEC admin password (minimum 8 characters)" -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
try {
    Set-Location -LiteralPath $RuntimeRoot
    $env:AYEC_ADMIN_EMAIL = "ayecpro@gmail.com"
    $env:AYEC_ADMIN_RESET_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    $env:AYEC_DB_PATH = $Database
    $env:AYEC_TENANT_DIR = $TenantDirectory
    & $Python $ResetScript
    if ($LASTEXITCODE -ne 0) {
        throw "Password reset failed. Review the message above and confirm this server database is available."
    }

    $verifyCode = "import Main,os,sys; p=(os.environ.get('AYEC_ADMIN_RESET_PASSWORD') or '').strip(); u=Main.authenticate_account('ayecpro@gmail.com',p,None); m=bool(u); a=bool(u and Main.is_control_admin(u)); print('LOCAL_PASSWORD_MATCH='+str(m)); print('LOCAL_SUPER_ADMIN='+str(a)); sys.exit(0 if m and a else 3)"
    & $Python -c $verifyCode
    if ($LASTEXITCODE -ne 0) {
        throw "The account was updated, but local login verification failed. Do not retry the Admin Console yet."
    }

    Write-Host "Admin password reset completed. Sign in as ayecpro@gmail.com." -ForegroundColor Green
} finally {
    if ($bstr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
    Remove-Item Env:AYEC_ADMIN_RESET_PASSWORD -ErrorAction SilentlyContinue
    Remove-Item Env:AYEC_ADMIN_EMAIL -ErrorAction SilentlyContinue
    Remove-Item Env:AYEC_DB_PATH -ErrorAction SilentlyContinue
    Remove-Item Env:AYEC_TENANT_DIR -ErrorAction SilentlyContinue
}
