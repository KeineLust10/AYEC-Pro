@echo off
setlocal
set "AYEC_APP=%~dp0."
if exist "%AYEC_APP%\Main.py" goto app_found
if exist "%AYEC_APP%\Web_Arayuzu\Main.py" set "AYEC_APP=%AYEC_APP%\Web_Arayuzu"
if exist "%AYEC_APP%\Main.py" goto app_found
if exist "%AYEC_APP%\..\Main.py" set "AYEC_APP=%AYEC_APP%\.."
if exist "%AYEC_APP%\Main.py" goto app_found
if exist "C:\Web_Arayuzu\Main.py" set "AYEC_APP=C:\Web_Arayuzu"
if exist "%AYEC_APP%\Main.py" goto app_found
echo AYEC application directory was not found. Expected Main.py beside this file or in C:\Web_Arayuzu.
pause
exit /b 1
:app_found
set "AYEC_PYTHON=%AYEC_APP%\.venv\Scripts\python.exe"
if not exist "%AYEC_PYTHON%" (
  echo AYEC Python environment was not found. Run server-windows-install.ps1 first.
  pause
  exit /b 1
)
"%AYEC_PYTHON%" "%AYEC_APP%\tools\configure_official_smtp.py" --application-path "%AYEC_APP%"
set "AYEC_RESULT=%ERRORLEVEL%"
pause
exit /b %AYEC_RESULT%
