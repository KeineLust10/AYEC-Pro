param(
    [string]$TargetUrl = "http://localhost:5173",
    [string]$ApiUrl = "http://localhost:8000",
    [string]$ScanMode = "quick"
)

$ErrorActionPreference = "Stop"

$Root = (Resolve-Path "$PSScriptRoot\..").Path
$FrontendPath = Join-Path $Root "frontend"
$BackendPath = Join-Path $Root "backend\app"
$InstructionTemplate = Join-Path $Root "security\strix\instruction.md"
$ReportsDir = Join-Path $Root "reports\strix"
$InstructionFile = Join-Path $ReportsDir "instruction.runtime.md"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogFile = Join-Path $ReportsDir "strix_scan_$Timestamp.log"

if (-not (Get-Command strix -ErrorAction SilentlyContinue)) {
    Write-Error "Strix CLI not found. Install with 'pipx install strix-agent' or 'curl -sSL https://strix.ai/install | bash'."
}

New-Item -ItemType Directory -Force -Path $ReportsDir | Out-Null

$instruction = Get-Content -Raw -Path $InstructionTemplate
$instruction = $instruction.Replace('${TARGET_URL}', $TargetUrl).Replace('${API_URL}', $ApiUrl)
$instruction | Set-Content -Encoding UTF8 -Path $InstructionFile

Write-Host "Strix scan başlatılıyor..."
Write-Host "TargetUrl: $TargetUrl"
Write-Host "ApiUrl: $ApiUrl"
Write-Host "ScanMode: $ScanMode"

strix -n `
    --scan-mode $ScanMode `
    --instruction-file $InstructionFile `
    -t $FrontendPath `
    -t $BackendPath `
    -t $TargetUrl `
    -t "$ApiUrl/docs" 2>&1 | Tee-Object -FilePath $LogFile

$exitCode = $LASTEXITCODE
Write-Host "Strix scan tamamlandı. Log: $LogFile"
exit $exitCode
