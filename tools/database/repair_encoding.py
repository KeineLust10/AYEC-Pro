import os

content = r"""# BuildSetup.ps1 - AYEC Pro Complete Build Automation

Write-Host ""
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host "        PREMIUM BULUT - SETUP BUILDER v2.10               " -ForegroundColor Cyan
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$ErrorActionPreference = "Stop"
$InnoSetupPath = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

# Step 0: Check Prerequisites
Write-Host "[0/6] Checking prerequisites..." -ForegroundColor Yellow

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  [OK] Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  [Error] Python not found! Please install Python 3.8+" -ForegroundColor Red
    exit 1
}

# Check PyInstaller
try {
    $pyinstallerVersion = pyinstaller --version 2>&1
    Write-Host "  [OK] PyInstaller: $pyinstallerVersion" -ForegroundColor Green
} catch {
    Write-Host "  [!] PyInstaller not found. Installing..." -ForegroundColor Yellow
    pip install pyinstaller
}

# Check Inno Setup
if (-not (Test-Path -Path $InnoSetupPath)) {
    Write-Host "  [Error] Inno Setup not found at: $InnoSetupPath" -ForegroundColor Red
    Write-Host "      Please install from: https://jrsoftware.org/isdl.php" -ForegroundColor Yellow
    exit 1
} else {
    Write-Host "  [OK] Inno Setup found" -ForegroundColor Green
}

Write-Host ""

# Step 1: Clean previous builds
Write-Host "[1/6] Cleaning previous builds..." -ForegroundColor Yellow
$foldersToClean = @("dist", "build", "Setup_Output")
foreach ($folder in $foldersToClean) {
    if (Test-Path -Path $folder) {
        Remove-Item $folder -Recurse -Force
        Write-Host "  [OK] Cleaned: $folder" -ForegroundColor Green
    }
}
Write-Host ""

# Step 2: Convert PNG logos to BMP (if needed)
Write-Host "[2/6] Preparing logo assets..." -ForegroundColor Yellow

# Check if BMP files exist, if not, try to convert
$pngToBmp = @{
    "assets\setup_wizard_large.png" = "assets\setup_wizard_large.bmp"
    "assets\setup_wizard_small.png" = "assets\setup_wizard_small.bmp"
}

foreach ($png in $pngToBmp.Keys) {
    $bmp = $pngToBmp[$png]
    if ((Test-Path -Path $png) -and -not (Test-Path -Path $bmp)) {
        Write-Host "  [i] Converting $png to BMP..." -ForegroundColor Yellow
        # Try using ImageMagick if available
        try {
            magick convert $png $bmp 2>&1 | Out-Null
            Write-Host "  [OK] Converted: $(Split-Path $bmp -Leaf)" -ForegroundColor Green
        } catch {
            Write-Host "  [!] ImageMagick not found. Please convert manually if needed." -ForegroundColor Yellow
        }
    } elseif (Test-Path -Path $bmp) {
        Write-Host "  [OK] Found: $(Split-Path $bmp -Leaf)" -ForegroundColor Green
    }
}

# Check for ICO file
if (-not (Test-Path -Path "assets\app_icon.ico")) {
    if (Test-Path -Path "assets\app_icon.png") {
        Write-Host "  [!] app_icon.ico not found. Please convert app_icon.png to ICO format" -ForegroundColor Yellow
        Write-Host "      Use online tool: https://convertio.co/png-ico/" -ForegroundColor Yellow
    } else {
        Write-Host "  [Error] app_icon.ico not found!" -ForegroundColor Red
    }
} else {
    Write-Host "  [OK] Found: app_icon.ico" -ForegroundColor Green
}

Write-Host ""

# Step 3: Build Desktop App
Write-Host "[3/6] Building Desktop Application..." -ForegroundColor Yellow
try {
    # Clean build
    pyinstaller --clean AYECPro_App.spec 2>&1 | Out-Null
    
    if (Test-Path -Path "dist\AYECPro_App.exe") {
        $appSize = (Get-Item "dist\AYECPro_App.exe").Length / 1MB
        $appSizeRounded = [math]::Round($appSize, 2)
        Write-Host "  [OK] Desktop App built successfully $appSizeRounded MB" -ForegroundColor Green
    } else {
        throw "Build failed - Executable not found"
    }
} catch {
    Write-Host "  [Error] Desktop app build failed!" -ForegroundColor Red
    Write-Host "      Error: $_" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 4: Build Server
Write-Host "[4/6] Building Server Application..." -ForegroundColor Yellow
try {
    pyinstaller --clean AYECPro_Server.spec 2>&1 | Out-Null
    
    if (Test-Path -Path "dist\AYECPro_Server.exe") {
        $serverSize = (Get-Item "dist\AYECPro_Server.exe").Length / 1MB
        $serverSizeRounded = [math]::Round($serverSize, 2)
        Write-Host "  [OK] Server built successfully $serverSizeRounded MB" -ForegroundColor Green
    } else {
        throw "Build failed - Executable not found"
    }
} catch {
    Write-Host "  [Error] Server build failed!" -ForegroundColor Red
    Write-Host "      Error: $_" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 5: Verify required files
Write-Host "[5/6] Verifying build output..." -ForegroundColor Yellow
$requiredFiles = @(
    "dist\AYECPro_App.exe",
    "dist\AYECPro_Server.exe",
    "StartServer.cmd",
    "ConfigureFirewall.cmd",
    "StopServer.cmd",
    "README.md",
    "setup.iss"
)

$allFilesExist = $true
foreach ($file in $requiredFiles) {
    if (Test-Path -Path $file) {
        Write-Host "  [OK] $(Split-Path $file -Leaf)" -ForegroundColor Green
    } else {
        Write-Host "  [Error] Missing: $file" -ForegroundColor Red
        $allFilesExist = $false
    }
}

if (-not $allFilesExist) {
    Write-Host ""
    Write-Host "  [Error] Some required files are missing!" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 6: Build Setup
Write-Host "[6/6] Creating installer package..." -ForegroundColor Yellow
try {
    & $InnoSetupPath setup.iss 2>&1 | Out-Null
    
    if ($LASTEXITCODE -eq 0) {
        if (Test-Path -Path "Setup_Output\AYECPro_Setup_v2.10.exe") {
            $setupSize = (Get-Item "Setup_Output\AYECPro_Setup_v2.10.exe").Length / 1MB
            $setupSizeRounded = [math]::Round($setupSize, 2)
            Write-Host "  [OK] Setup created successfully $setupSizeRounded MB" -ForegroundColor Green
        } else {
            throw "Setup file not found"
        }
    } else {
        throw "Inno Setup compilation failed"
    }
} catch {
    Write-Host "  [Error] Setup creation failed!" -ForegroundColor Red
    Write-Host "      Error: $_" -ForegroundColor Red
    exit 1
}

# Success!
Write-Host ""
Write-Host "===========================================================" -ForegroundColor Green
Write-Host "              BUILD COMPLETED SUCCESSFULLY!                " -ForegroundColor Green
Write-Host "===========================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Setup File: .\Setup_Output\AYECPro_Setup_v2.10.exe" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Test the installer on a clean Windows machine" -ForegroundColor White
Write-Host "  2. Verify all features work correctly" -ForegroundColor White
Write-Host "  3. Distribute to users" -ForegroundColor White
Write-Host ""
Write-Host "  Press any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
"""

with open("BuildSetup.ps1", "w", encoding="utf-8-sig") as f:
    f.write(content)
print("BuildSetup.ps1 repaired with UTF-8 BOM encoding.")
