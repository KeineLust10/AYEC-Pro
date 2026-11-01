@echo off
setlocal
set "AYEC_APP=%~dp0"
set "AYEC_PYTHON=%AYEC_APP%.venv\Scripts\python.exe"
if not exist "%AYEC_PYTHON%" (
  echo AYEC Python environment was not found. Run server-windows-install.ps1 first.
  exit /b 1
)
"%AYEC_PYTHON%" "%AYEC_APP%tools\configure_google_oauth.py" --application-path "%AYEC_APP%" %*
exit /b %ERRORLEVEL%
