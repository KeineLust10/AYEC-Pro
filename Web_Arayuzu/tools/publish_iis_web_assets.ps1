[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$SourceRoot,
    [Parameter(Mandatory = $true)][string]$SiteRoot,
    [Parameter(Mandatory = $true)][string]$BackupRoot
)

$ErrorActionPreference = "Stop"
$sourceFullPath = [System.IO.Path]::GetFullPath($SourceRoot)
$siteFullPath = [System.IO.Path]::GetFullPath($SiteRoot)
$sitePrefix = $siteFullPath.TrimEnd('\') + '\'
$indexPath = Join-Path $sourceFullPath "index.html"
if (-not (Test-Path -LiteralPath $indexPath -PathType Leaf)) {
    throw "AYEC web assets were not found under $sourceFullPath."
}

$publishedFileCount = 0
$webFiles = Get-ChildItem -LiteralPath $sourceFullPath -File -Recurse | Where-Object {
    $_.FullName.Substring($sourceFullPath.Length).TrimStart('\', '/') -notmatch '(^|[\\/])uploads([\\/]|$)'
}
foreach ($sourceFile in $webFiles) {
    $relativePath = $sourceFile.FullName.Substring($sourceFullPath.Length).TrimStart('\', '/')
    $targetPath = Join-Path $siteFullPath $relativePath
    $targetFullPath = [System.IO.Path]::GetFullPath($targetPath)
    if (-not $targetFullPath.StartsWith($sitePrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Web asset path escapes the IIS site root: $relativePath"
    }
    if (Test-Path -LiteralPath $targetPath -PathType Leaf) {
        $backupPath = Join-Path $BackupRoot $relativePath
        New-Item -ItemType Directory -Path (Split-Path -Parent $backupPath) -Force | Out-Null
        Copy-Item -LiteralPath $targetPath -Destination $backupPath -Force
    }
    New-Item -ItemType Directory -Path (Split-Path -Parent $targetPath) -Force | Out-Null
    Copy-Item -LiteralPath $sourceFile.FullName -Destination $targetPath -Force
    $publishedFileCount++
}

Write-Output $publishedFileCount
