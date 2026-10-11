@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0RESET_ADMIN_PASSWORD.ps1"
echo.
pause
endlocal
