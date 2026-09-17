[CmdletBinding()]
param(
    [string]$PublicUrl = "http://85.117.239.60",
    [int]$Port = 8501,
    [string]$PublicIp = "85.117.239.60"
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
$ProjectPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectPath

# Baslat.ps1 tarafindan acilan Python sureci ayni sunucu ortamini kullansin.
$TenantDirectory = Join-Path $ProjectPath ("Kullan" + [char]0x0131 + "c" + [char]0x0131 + "lar")
New-Item -ItemType Directory -Path $TenantDirectory -Force | Out-Null
$env:AYEC_HOST = "127.0.0.1"
$env:AYEC_PORT = "$Port"
$env:AYEC_DB_PATH = Join-Path $ProjectPath "data\ayecpro.db"
$env:AYEC_TENANT_DIR = $TenantDirectory
$env:AYEC_BACKUP_DIR = Join-Path $ProjectPath "backups"
$env:EASYOCR_MODULE_PATH = Join-Path $ProjectPath "ocr-models\EasyOCR"
$env:USERPROFILE = Join-Path $ProjectPath "ocr-models"
$env:PYTHONUTF8 = "1"
$env:PYTHONUNBUFFERED = "1"

# ZIP yeni bir sunucuya ilk kez aciliyorsa kurulumu da bu tek tik tamamlar.
$VenvPython = Join-Path $ProjectPath ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $VenvPython)) {
    Write-Host "Ilk kurulum yapiliyor; bu adim internet ve Yonetici izni gerektirir..." -ForegroundColor Yellow
    & (Join-Path $ProjectPath "server-windows-install.ps1") -PublicIp $PublicIp -BackendPort $Port
    if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) {
        throw "Ilk kurulum basarisiz oldu (kod: $LASTEXITCODE)."
    }
}

Write-Host "AYEC Pro Web baslatiliyor..." -ForegroundColor Cyan
$StartScript = Join-Path $ProjectPath "baslat.ps1"
& $StartScript -HostAddress "127.0.0.1" -Port $Port -BrowserUrl $PublicUrl
if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) {
    throw "Web uygulamasi baslatilamadi (kod: $LASTEXITCODE)."
}

try {
    Import-Module WebAdministration -ErrorAction Stop
    $site = Get-Website -Name "Default Web Site" -ErrorAction SilentlyContinue
    if ($site -and $site.State -ne "Started") {
        Start-Website -Name "Default Web Site"
        Write-Host "IIS Default Web Site baslatildi." -ForegroundColor Green
    }
}
catch {
    Write-Warning "IIS otomatik baslatilamadi: $($_.Exception.Message)"
}

Write-Host "AYEC Pro Web hazir: $PublicUrl" -ForegroundColor Green
