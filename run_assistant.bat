@echo off
SETLOCAL ENABLEDELAYEDEXPANSION
SET "PROJECT_DIR=%~dp0"
SET "PYTHON_VENV=%PROJECT_DIR%venv\Scripts\activate.bat"
SET "STREAMLIT_APP=%PROJECT_DIR%app.py"
SET "PORT=8501"

:menu
cls
echo ==========================================================
echo           KHOI DONG TRO LY AI CA NHAN
echo ==========================================================
echo.
echo 1. Ollama + Assistant + Ngrok
echo 2. Assistant + Ngrok (Ollama da chay)
echo 3. Chi Ollama
echo 4. Thoat
echo.
set /p choice="Nhap lua chon (1-4): "

if "%choice%"=="1" goto start_all
if "%choice%"=="2" goto start_assistant_only
if "%choice%"=="3" goto start_ollama_only
if "%choice%"=="4" goto exit
goto menu

:start_all
start "Ollama Server" cmd /k "ollama serve"
timeout /t 5 >nul
goto start_assistant_only

:start_assistant_only
if not exist "%PYTHON_VENV%" (
    echo [ERROR] Khong tim thay moi truong ao.
    pause
    goto exit
)
call "%PYTHON_VENV%"

REM Debug tung buoc
cd /d "%PROJECT_DIR%"
echo Da cd xong
echo Dang chay streamlit...
REM Chay Streamlit trong cua so moi, chuyen dung thu muc va kich hoat venv
start "Streamlit" cmd /k "cd /d %PROJECT_DIR% && call venv\Scripts\activate.bat && streamlit run app.py --server.address 0.0.0.0 --server.port %PORT%"

REM Chay ngrok
start "Ngrok" cmd /k "ngrok http %PORT%"
timeout /t 5 >nul

REM Lay link ngrok
set "url="
for /f "tokens=2 delims=: " %%a in ('curl -s http://127.0.0.1:4040/api/tunnels ^| findstr /i "public_url"') do (
    set "url=%%a"
)
set "url=%url:~2,-2%"

if "%url%"=="" (
    echo [ERROR] Khong lay duoc link Ngrok.
    pause
    goto exit
)

echo [INFO] Mo trinh duyet: %url%
start "" "%url%"
goto exit

:start_ollama_only
start "Ollama Server" cmd /k "ollama serve"
goto exit

:exit
echo [INFO] Hoan tat.
exit
