@echo off
python "%~dp0check_public_deployment.py" %*
exit /b %ERRORLEVEL%
