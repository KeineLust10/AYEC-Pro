$ErrorActionPreference = "Stop"
$installRoot = "C:\AYECPro-Demo"
$envPath = Join-Path $installRoot "demo.env"
$appRoot = Join-Path $installRoot "App"
$logRoot = Join-Path $installRoot "Data\logs"

if (-not (Test-Path -LiteralPath $envPath -PathType Leaf)) {
    throw "Demo environment file is missing."
}
if (-not (Test-Path -LiteralPath (Join-Path $installRoot "Data\.ayec-demo-sandbox") -PathType Leaf)) {
    throw "Demo sandbox marker is missing."
}

$demoVariables = @{}
foreach ($line in Get-Content -LiteralPath $envPath) {
    $trimmed = $line.Trim()
    if (-not $trimmed -or $trimmed.StartsWith("#")) { continue }
    $pair = $trimmed -split "=", 2
    if ($pair.Count -ne 2) { throw "Invalid demo environment entry." }
    $demoVariables[$pair[0].Trim()] = $pair[1].Trim()
}

Get-ChildItem Env: | Where-Object { $_.Name -match '^(AYEC_|AYECPRO_)' } | ForEach-Object {
    Remove-Item -LiteralPath ("Env:" + $_.Name)
}
foreach ($name in $demoVariables.Keys) {
    [Environment]::SetEnvironmentVariable($name, $demoVariables[$name], "Process")
}

$python = [Environment]::GetEnvironmentVariable("AYEC_DEMO_PYTHON", "Process")
if (-not $python) {
    $command = Get-Command python.exe -ErrorAction Stop
    $python = $command.Source
}
$main = Join-Path $appRoot "Main.py"
if (-not (Test-Path -LiteralPath $main -PathType Leaf)) { throw "Demo app entry point is missing." }
if (-not (Test-Path -LiteralPath $env:AYEC_DEMO_TEMPLATE -PathType Leaf)) { throw "Demo seed database is missing." }
if (-not (Test-Path -LiteralPath $logRoot -PathType Container)) {
    New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
}
$stdout = Join-Path $logRoot "demo.stdout.log"
$stderr = Join-Path $logRoot "demo.stderr.log"
Set-Location -LiteralPath $appRoot
& $python $main --host $env:AYEC_HOST --port $env:AYEC_PORT --db $env:AYEC_DB_PATH --tenant-dir $env:AYEC_TENANT_DIR 1>> $stdout 2>> $stderr
exit $LASTEXITCODE
