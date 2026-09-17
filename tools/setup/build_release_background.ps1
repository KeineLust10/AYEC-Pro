[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$OutputDir = Join-Path $ProjectRoot "Setup_Output"
$LogPath = Join-Path $OutputDir "release_build.log"
$Python = Join-Path $ProjectRoot ".venv_active\Scripts\python.exe"
$MaxBuildAttempts = 3

function Write-BuildLog {
    param([string]$Message)
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -LiteralPath $LogPath -Value "$stamp $Message" -Encoding UTF8
}

try {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    Write-BuildLog "Build started"
    Push-Location $ProjectRoot
    try {
        $BuildCommand = '"{0}" -u tools\setup\build_nuitka.py >> "{1}" 2>&1' -f $Python, $LogPath
        $Attempt = 1
        while ($true) {
            & cmd.exe /d /c $BuildCommand
            if ($LASTEXITCODE -eq 0) {
                break
            }
            if ($Attempt -ge $MaxBuildAttempts) {
                throw "Nuitka build failed with exit code $LASTEXITCODE"
            }
            Write-BuildLog "Build retry scheduled after failed attempt $Attempt"
            $Attempt += 1
        }

        $HealthCommand = '"dist\AYECPro_App\bin\AYECPro.Core.exe" --healthcheck >> "{0}" 2>&1' -f $LogPath
        & cmd.exe /d /c $HealthCommand
        if ($LASTEXITCODE -ne 0) {
            throw "Compiled healthcheck failed with exit code $LASTEXITCODE"
        }
    }
    finally {
        Pop-Location
    }
    Write-BuildLog "Build completed successfully; shutdown skipped by operator request"
}
catch {
    Write-BuildLog "Build failed: $($_.Exception.Message)"
    exit 1
}
