$ErrorActionPreference = "Stop"
$installRoot = "C:\AYECPro-Demo"
$envPath = Join-Path $installRoot "demo.env"
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
if (-not $python) { $python = (Get-Command python.exe -ErrorAction Stop).Source }
$cleanup = Join-Path $installRoot "demo_site\reset_demo_sessions.py"
& $python $cleanup --age-hours 3
exit $LASTEXITCODE
