@echo off
chcp 65001 >nul
set "AYEC_START_SCRIPT=%~dp0AYEC_PRO_TEK_TIK_BASLAT.ps1"

echo AYEC Pro Web baslatiliyor...
echo Gerekirse Yonetici izni isteyen pencereyi onaylayin.

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$a=@('-NoProfile','-ExecutionPolicy','Bypass','-File',$env:AYEC_START_SCRIPT); $p=Start-Process -FilePath 'powershell.exe' -Verb RunAs -Wait -PassThru -ArgumentList $a; exit $p.ExitCode"
if errorlevel 1 (
  echo.
  echo Baslatma basarisiz oldu. logs\server.error.log ve logs\server.out.log dosyalarini kontrol edin.
  pause
  exit /b 1
)

echo.
echo AYEC Pro Web baslatildi. Tarayici acilmasi bekleniyor.
pause
