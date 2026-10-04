@echo off
setlocal
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
    echo Python environment not found. Run these commands in mrt-ai:
    echo py -3.11 -m venv venv
    echo venv\Scripts\python.exe -m pip install -r requirements.txt
    exit /b 1
)
set "CHAT_PORT=0"
if not "%~1"=="" set "CHAT_PORT=%~1"
"venv\Scripts\python.exe" -X utf8 -B -m scripts.dev --port "%CHAT_PORT%"
exit /b %errorlevel%
