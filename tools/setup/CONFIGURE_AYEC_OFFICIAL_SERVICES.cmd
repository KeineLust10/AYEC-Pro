@echo off
setlocal
set "AYEC_APP=C:\Web_Arayuzu"
if not exist "%AYEC_APP%\Main.py" set /p "AYEC_APP=AYEC server application folder: "
if not exist "%AYEC_APP%\.venv\Scripts\python.exe" (
  echo Python environment not found in the application folder.
  pause
  exit /b 1
)
"%AYEC_APP%\.venv\Scripts\python.exe" "%~dp0configure_official_services.py" --application-path "%AYEC_APP%"
pause
