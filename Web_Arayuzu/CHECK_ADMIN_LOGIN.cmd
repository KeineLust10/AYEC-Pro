@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0CHECK_ADMIN_LOGIN.ps1"
echo.
pause
endlocal
