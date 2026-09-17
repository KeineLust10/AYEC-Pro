@echo off
set "AYEC_UPDATE_ROOT=%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Start-Process powershell.exe -Verb RunAs -Wait -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File \"%AYEC_UPDATE_ROOT%RUN_AYEC_SERVER_UPDATE.ps1\"'"
if errorlevel 1 (
  echo AYEC server update failed. Review the PowerShell error above.
  pause
  exit /b 1
)
echo AYEC server update completed.
pause
