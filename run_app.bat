@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv_active\Scripts\python.exe" (
    echo Workspace Python environment is missing.
    pause
    exit /b 1
)
start "" "%~dp0.venv_active\Scripts\python.exe" "%~dp0Main.py"
