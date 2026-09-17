[CmdletBinding()]
param(
    [string]$Domain = "panel.ayecpro.com",
    [string]$ExpectedIp = "85.117.239.60",
    [string]$EmailAddress = "ayecpro@gmail.com",
    [string]$SiteName = "Default Web Site"
)

$ErrorActionPreference = "Stop"

function Assert-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Run PowerShell as Administrator."
    }
}

Assert-Administrator

$resolved = [System.Net.Dns]::GetHostAddresses($Domain) |
    Where-Object AddressFamily -eq InterNetwork |
    Select-Object -ExpandProperty IPAddressToString -Unique
if ($ExpectedIp -notin $resolved) {
    throw "$Domain does not resolve to $ExpectedIp yet. Current result: $($resolved -join ', ')"
}

Import-Module WebAdministration
$site = Get-Website -Name $SiteName -ErrorAction Stop
$siteId = [int]$site.Id
$httpBinding = Get-WebBinding -Name $SiteName -Protocol "http" |
    Where-Object bindingInformation -eq "*:80:$Domain"
if (-not $httpBinding) {
    New-WebBinding -Name $SiteName -Protocol "http" -Port 80 -IPAddress "*" -HostHeader $Domain
}

$ruleName = "AYEC Pro HTTPS 443"
if (-not (Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort 443 | Out-Null
}

$installRoot = Join-Path $env:ProgramFiles "win-acme"
$wacs = Join-Path $installRoot "wacs.exe"
if (-not (Test-Path -LiteralPath $wacs)) {
    $downloadUrl = "https://github.com/win-acme/win-acme/releases/download/v2.2.9.1701/win-acme.v2.2.9.1701.x64.trimmed.zip"
    $archive = Join-Path $env:TEMP "win-acme.v2.2.9.1701.x64.trimmed.zip"
    New-Item -ItemType Directory -Path $installRoot -Force | Out-Null
    Invoke-WebRequest -Uri $downloadUrl -OutFile $archive -UseBasicParsing
    Expand-Archive -LiteralPath $archive -DestinationPath $installRoot -Force
}
if (-not (Test-Path -LiteralPath $wacs)) {
    throw "win-acme installation failed."
}

$arguments = @(
    "--source", "iis",
    "--siteid", "$siteId",
    "--host", $Domain,
    "--validation", "selfhosting",
    "--store", "certificatestore",
    "--installation", "iis",
    "--installationsiteid", "$siteId",
    "--emailaddress", $EmailAddress,
    "--accepttos"
)
& $wacs @arguments
if ($LASTEXITCODE -ne 0) {
    throw "Certificate request failed with exit code $LASTEXITCODE."
}

$httpsBinding = Get-WebBinding -Name $SiteName -Protocol "https" |
    Where-Object bindingInformation -match ":443:$([regex]::Escape($Domain))$"
if (-not $httpsBinding) {
    $certificate = Get-ChildItem Cert:\LocalMachine\WebHosting |
        Where-Object {
            $_.Subject -eq "CN=$Domain" -or
            $_.DnsNameList.Unicode -contains $Domain
        } |
        Sort-Object NotAfter -Descending |
        Select-Object -First 1
    if (-not $certificate) {
        throw "The certificate exists in win-acme but was not found in the WebHosting store."
    }
    New-WebBinding -Name $SiteName -Protocol "https" -Port 443 -IPAddress "*" -HostHeader $Domain -SslFlags 1
    $httpsBinding = Get-WebBinding -Name $SiteName -Protocol "https" |
        Where-Object bindingInformation -match ":443:$([regex]::Escape($Domain))$"
    $httpsBinding.AddSslCertificate($certificate.Thumbprint, "WebHosting")
}

Start-Sleep -Seconds 2
$response = Invoke-WebRequest -Uri "https://$Domain/api/desktop/health" -UseBasicParsing -TimeoutSec 20
if ($response.StatusCode -ne 200) {
    throw "HTTPS health check failed with status $($response.StatusCode)."
}

Write-Host "HTTPS setup completed: https://$Domain" -ForegroundColor Green
Write-Host "Automatic certificate renewal is enabled." -ForegroundColor Green
