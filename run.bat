@echo off
setlocal ENABLEDELAYEDEXPANSION

REM One-click launcher for Assistant (Flask + static UI) on Windows
set "PROJECT_DIR=%~dp0"
pushd "%PROJECT_DIR%"

set "VENV_DIR=%PROJECT_DIR%venv"
set "VENV_ACT=%VENV_DIR%\Scripts\activate.bat"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
set "PIP_EXE=%VENV_DIR%\Scripts\pip.exe"
set "APP_URL=http://localhost:8000"
REM Set your reserved ngrok domain here (must be configured in your ngrok account)
set "NGROK_DOMAIN=skylark-simple-bullfrog.ngrok-free.app"

echo ==========================================================
echo   Starting Personal Assistant (Flask + static UI)
echo ==========================================================

REM Create venv if missing
if not exist "%PYTHON_EXE%" (
    echo [SETUP] Creating virtual environment...
    py -3 -m venv "%VENV_DIR%"
)

REM Ensure pip and requirements
echo [SETUP] Installing/Updating dependencies...
call "%VENV_ACT%"
"%PIP_EXE%" --disable-pip-version-check -q install --upgrade pip >nul 2>&1
"%PIP_EXE%" -q install -r requirements.txt

REM Start Ollama if available
where ollama >nul 2>&1
if %ERRORLEVEL%==0 (
    echo [RUN] Launching Ollama server...
    start "Ollama Server" cmd /k "ollama serve"
) else (
    echo [WARN] Ollama CLI not found. Skipping ollama serve.
)

REM Start Flask server
echo [RUN] Launching Assistant server (Flask)...
start "Assistant Server" cmd /k "call %VENV_ACT% && python server.py"

REM Start ngrok with reserved domain if available
where ngrok >nul 2>&1
if %ERRORLEVEL%==0 (
    if defined NGROK_DOMAIN (
        echo [RUN] Launching ngrok: https://%NGROK_DOMAIN%
        start "Ngrok Tunnel" cmd /k "ngrok http --domain=%NGROK_DOMAIN% 8000"
        REM Give ngrok a moment to establish the tunnel
        timeout /t 3 /nobreak >nul
        set "BROWSER_URL=https://%NGROK_DOMAIN%"
    ) else (
        echo [WARN] NGROK_DOMAIN not set. Skipping fixed-domain tunnel.
        set "BROWSER_URL=%APP_URL%"
    )
) else (
    echo [WARN] ngrok CLI not found. Opening local URL.
    set "BROWSER_URL=%APP_URL%"
)

REM Open browser to the chosen URL
echo [OPEN] %BROWSER_URL%
start "" "%BROWSER_URL%"

echo [INFO] All set. Close this window if not needed.
popd
exit /b 0