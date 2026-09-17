[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$OutputDir = Join-Path $ProjectRoot "Setup_Output"
$BuildLog = Join-Path $OutputDir "release_build.log"
$MonitorLog = Join-Path $OutputDir "release_monitor.log"
$MaxRestarts = 2
$RestartCount = 0

function Write-MonitorLog {
    param([string]$Message)
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -LiteralPath $MonitorLog -Value "$stamp $Message" -Encoding UTF8
}

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

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
while ($true) {
    if (Get-BuildWorker) {
        Write-MonitorLog "Build is active"
        Start-Sleep -Seconds 300
        continue
    }

    $lastLine = ""
    if (Test-Path -LiteralPath $BuildLog) {
        $lastLine = Get-Content -LiteralPath $BuildLog -Tail 40 |
            Where-Object { $_.Trim() } |
            Select-Object -Last 1
    }
    if ($lastLine -match "Build completed successfully") {
        Write-MonitorLog "Build completed successfully"
        exit 0
    }
    if ($lastLine -match "Build failed" -and $RestartCount -lt $MaxRestarts) {
        $RestartCount += 1
        Write-MonitorLog "Build failed, starting retry $RestartCount"
        Start-BuildWorker
        Start-Sleep -Seconds 300
        continue
    }
    Write-MonitorLog "Build monitor stopped: no active worker"
    exit 1
}
