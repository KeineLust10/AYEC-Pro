$innoPaths = @('C:\Program Files (x86)\Inno Setup 6\ISCC.exe','C:\Program Files\Inno Setup 6\ISCC.exe')
$found = $null
foreach($p in $innoPaths){ if(Test-Path $p){ $found = $p; break }}
if(-not $found){ Write-Host "Inno Setup not found at standard locations."; exit 2 }

$issList = @('Setup_Files\AYECPro_Desktop_Setup.iss','Setup_Files\AYECPro_Server_Setup.iss','Setup_Files\AYECPro_Setup.iss')
foreach($iss in $issList){
    Write-Host "Compiling: $iss"
    & "$found" $iss
    if($LASTEXITCODE -ne 0){
        Write-Host "[ERROR] Failed: $iss with exit code $LASTEXITCODE"
        exit $LASTEXITCODE
    }
}

Write-Host "All installers compiled successfully. Output in dist\\"
exit 0
