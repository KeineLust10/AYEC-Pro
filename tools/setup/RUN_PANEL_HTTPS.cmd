@echo off
set "AYEC_SSL_ROOT=%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Start-Process powershell.exe -Verb RunAs -Wait -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File \"%AYEC_SSL_ROOT%install_panel_https.ps1\"'"
if errorlevel 1 (
  echo AYEC HTTPS setup failed. Review the PowerShell error above.
  pause
  exit /b 1
)
echo AYEC HTTPS setup completed.
pause
