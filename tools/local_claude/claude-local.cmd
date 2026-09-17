@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "TARGET_DIR=%~1"
set "MODEL_NAME=%~2"

if "%TARGET_DIR%"=="" set "TARGET_DIR=C:\Users\yedek\Desktop\yapay zeka\AYEC Pro"
if "%MODEL_NAME%"=="" set "MODEL_NAME=qwen3-coder:30b"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%Start-Local-Claude.ps1" -ProjectPath "%TARGET_DIR%" -Model "%MODEL_NAME%"

endlocal
