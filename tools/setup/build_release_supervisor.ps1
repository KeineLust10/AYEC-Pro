[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$LogPath = Join-Path $ProjectRoot "Setup_Output\release_build.log"
$RetryCount = 0
$MaxRetries = 2

function Get-BuildWorker {
    Get-CimInstance Win32_Process | Where-Object {
        $_.ProcessId -ne $PID -and $_.CommandLine -match "build_release_background\.ps1"
    }
}

function Start-BuildWorker {
    Start-Process -FilePath "powershell.exe" `
        -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "tools\setup\build_release_background.ps1" `
        -WorkingDirectory $ProjectRoot `
        -WindowStyle Hidden | Out-Null
}

while ($true) {
    if (Get-BuildWorker) {
        Start-Sleep -Seconds 30
        continue
    }

    $lastLine = ""
    if (Test-Path -LiteralPath $LogPath) {
        $lastLine = Get-Content -LiteralPath $LogPath -Tail 30 |
            Where-Object { $_.Trim() } |
            Select-Object -Last 1
    }
    if ($lastLine -match "Build completed successfully") {
        exit 0
    }
    if ($lastLine -match "Build failed" -and $RetryCount -lt $MaxRetries) {
        $RetryCount += 1
        Start-BuildWorker
        Start-Sleep -Seconds 30
        continue
    }
    exit 1
}
