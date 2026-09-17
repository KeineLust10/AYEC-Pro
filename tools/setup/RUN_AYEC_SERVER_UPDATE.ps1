$ErrorActionPreference = "Stop"
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$package = Get-ChildItem -LiteralPath $scriptRoot -Filter "AYECPro_Web_Server_*.zip" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $package) {
    throw "AYEC web server package was not found next to this script."
}

$updater = Join-Path $scriptRoot "update_production_server.ps1"
if (-not (Test-Path -LiteralPath $updater)) {
    throw "Server update script is missing."
}

& $updater -PackagePath $package.FullName
