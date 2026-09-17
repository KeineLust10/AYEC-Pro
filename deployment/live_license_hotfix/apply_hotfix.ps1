param(
    [string]$Target = "C:\Web_Arayuzu"
)

$ErrorActionPreference = "Stop"

$targetPath = [System.IO.Path]::GetFullPath($Target)
$expectedTarget = [System.IO.Path]::GetFullPath("C:\Web_Arayuzu")
if (-not $targetPath.Equals($expectedTarget, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Target must be exactly C:\Web_Arayuzu."
}

$targetMain = Join-Path $targetPath "Main.py"
$payloadMain = Join-Path $PSScriptRoot "payload\Main.py"
if (-not (Test-Path -LiteralPath $targetMain -PathType Leaf)) {
    throw "Live Main.py was not found at $targetMain"
}
if (-not (Test-Path -LiteralPath $payloadMain -PathType Leaf)) {
    throw "Hotfix payload Main.py is missing."
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupDir = Join-Path $targetPath "backups\pre-license-api-$stamp"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
Copy-Item -LiteralPath $targetMain -Destination (Join-Path $backupDir "Main.py")

$dataDir = Join-Path $targetPath "data"
if (Test-Path -LiteralPath $dataDir -PathType Container) {
    Get-ChildItem -LiteralPath $dataDir -Filter "*.db" -File -ErrorAction SilentlyContinue |
        ForEach-Object {
            Copy-Item -LiteralPath $_.FullName -Destination $backupDir
        }
}

Copy-Item -LiteralPath $payloadMain -Destination $targetMain -Force

$python = Join-Path $targetPath ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    $python = "python"
}
& $python -m py_compile $targetMain
if ($LASTEXITCODE -ne 0) {
    Copy-Item -LiteralPath (Join-Path $backupDir "Main.py") -Destination $targetMain -Force
    throw "Main.py validation failed. The previous file was restored."
}

$task = Get-ScheduledTask -TaskName "AYEC Pro Web" -ErrorAction SilentlyContinue
if ($task) {
    Stop-ScheduledTask -TaskName "AYEC Pro Web" -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Start-ScheduledTask -TaskName "AYEC Pro Web"
} else {
    throw "Scheduled task 'AYEC Pro Web' was not found. Main.py was updated but service was not restarted."
}

Start-Sleep -Seconds 5
$body = '{"hardware_id":"","requester_email":""}'
try {
    Invoke-WebRequest -Uri "http://127.0.0.1:8501/api/license/status/device" `
        -Method Post -ContentType "application/json" -Body $body -UseBasicParsing | Out-Null
} catch {
    $response = $_.Exception.Response
    if ($null -eq $response -or [int]$response.StatusCode -ne 400) {
        throw "License endpoint verification failed: $($_.Exception.Message)"
    }
}

Write-Host "AYEC Pro license API hotfix completed." -ForegroundColor Green
Write-Host "Backup: $backupDir"
