param(
    [string]$HostName = "panel.ayecpro.com",
    [string]$TaskName = "AYEC Pro Web",
    [int]$DefaultBackendPort = 8501,
    [string]$OutputPath
)

$ErrorActionPreference = "Stop"
$ProjectPath = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
if (-not $OutputPath) {
    $OutputPath = Join-Path $ProjectPath "logs\server-502-diagnostic.json"
}

$result = [ordered]@{
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    host = $HostName
    project_root = $ProjectPath
    task_found = $false
    task_state = "unavailable"
    task_last_result = $null
    backend_port = $DefaultBackendPort
    backend_listener = $false
    backend_process_id = $null
    backend_process_name = $null
    backend_health_status = $null
    backend_health_ok = $false
    iis_site_name = $null
    iis_site_root = $null
    iis_proxy_target = $null
    iis_auth_api_status = $null
    iis_auth_api_content_type = $null
    server_error_log = (Join-Path $ProjectPath "logs\server.error.log")
    server_launcher_log = (Join-Path $ProjectPath "logs\server.launcher.log")
}

try {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
    $taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction Stop
    $result.task_found = $true
    $result.task_state = [string]$task.State
    $result.task_last_result = [int]$taskInfo.LastTaskResult
} catch {}

try {
    Import-Module WebAdministration -ErrorAction Stop
    $matches = @()
    foreach ($site in Get-Website) {
        foreach ($binding in $site.Bindings.Collection) {
            if ([string]$binding.bindingInformation -match [regex]::Escape($HostName)) {
                $matches += $site
                break
            }
        }
    }
    if ($matches.Count -eq 1) {
        $site = $matches[0]
        $siteRoot = [Environment]::ExpandEnvironmentVariables([string]$site.PhysicalPath)
        $result.iis_site_name = [string]$site.Name
        $result.iis_site_root = $siteRoot
        $configPath = Join-Path $siteRoot "web.config"
        if (Test-Path -LiteralPath $configPath) {
            $configText = Get-Content -LiteralPath $configPath -Raw
            $rewrite = [regex]::Match($configText, 'http://127\.0\.0\.1:(\d+)/\{R:1\}')
            if ($rewrite.Success) {
                $result.backend_port = [int]$rewrite.Groups[1].Value
                $result.iis_proxy_target = "http://127.0.0.1:$($result.backend_port)/{R:1}"
            }
        }
    }
} catch {}

try {
    $listener = Get-NetTCPConnection -State Listen -LocalPort ([int]$result.backend_port) -ErrorAction Stop | Select-Object -First 1
    if ($listener) {
        $result.backend_listener = $true
        $result.backend_process_id = [int]$listener.OwningProcess
        $process = Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue
        if ($process) { $result.backend_process_name = [string]$process.ProcessName }
    }
} catch {}

try {
    $health = Invoke-WebRequest -Uri "http://127.0.0.1:$($result.backend_port)/api/desktop/health" -TimeoutSec 5 -UseBasicParsing
    $result.backend_health_status = [int]$health.StatusCode
    $payload = $health.Content | ConvertFrom-Json -ErrorAction Stop
    $result.backend_health_ok = ($payload.ok -eq $true)
} catch {
    if ($_.Exception.Response) {
        $result.backend_health_status = [int]$_.Exception.Response.StatusCode
    }
}

try {
    $request = [System.Net.HttpWebRequest]::Create("http://127.0.0.1/api/auth/status")
    $request.Method = "GET"
    $request.Host = $HostName
    $request.Accept = "application/json"
    $response = [System.Net.HttpWebResponse]$request.GetResponse()
    $result.iis_auth_api_status = [int]$response.StatusCode
    $result.iis_auth_api_content_type = [string]$response.ContentType
    $response.Close()
} catch {
    if ($_.Exception.Response) {
        $result.iis_auth_api_status = [int]$_.Exception.Response.StatusCode
        $result.iis_auth_api_content_type = [string]$_.Exception.Response.ContentType
        $_.Exception.Response.Close()
    }
}

$outputDirectory = Split-Path -Parent $OutputPath
New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
$result | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $OutputPath -Encoding UTF8
Write-Output "Server diagnostic written to: $OutputPath"
Write-Output "Backend health: $($result.backend_health_status) (ok=$($result.backend_health_ok)); IIS auth API: $($result.iis_auth_api_status)"
