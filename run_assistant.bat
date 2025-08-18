@echo off
SETLOCAL ENABLEDELAYEDEXPANSION
SET "PROJECT_DIR=%~dp0"
SET "PYTHON_VENV=%PROJECT_DIR%venv\Scripts\activate.bat"
SET "STREAMLIT_APP=%PROJECT_DIR%app.py"
SET "PORT=8501"
SET "NGROK_STATIC_DOMAIN=skylark-simple-bullfrog.ngrok-free.app"

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
REM Chạy Ollama trong một cửa sổ riêng
start "Ollama Server" cmd /k "ollama serve"
REM Chờ một chút để Ollama khởi động hoàn toàn (có thể điều chỉnh thời gian này nếu cần)
timeout /t 5 >nul
goto start_assistant_only

:start_assistant_only
REM Kiểm tra xem môi trường ảo Python đã tồn tại chưa
if not exist "%PYTHON_VENV%" (
    echo [ERROR] Khong tim thay moi truong ao Python tai: %PYTHON_VENV%
    pause
    goto exit
)
REM Kích hoạt môi trường ảo Python
call "%PYTHON_VENV%"

REM Thay đổi thư mục làm việc sang thư mục dự án
cd /d "%PROJECT_DIR%"
echo Da cd xong den thu muc: %CD%

REM Chạy ứng dụng Streamlit trong một cửa sổ mới
echo Dang chay Streamlit...
start "Streamlit App" cmd /k "call %PYTHON_VENV% && streamlit run app.py --server.address 0.0.0.0 --server.port %PORT%"

REM Chạy ngrok với static domain đã chỉ định
echo Dang chay ngrok voi static domain: %NGROK_STATIC_DOMAIN%
start "Ngrok Tunnel" cmd /k "ngrok http --domain=%NGROK_STATIC_DOMAIN% %PORT%"

REM Thông báo cho người dùng biết cách truy cập ứng dụng
echo.
echo [INFO] De truy cap ung dung, ban co the su dung dia chi:
echo      https://%NGROK_STATIC_DOMAIN%
echo.
echo [INFO] Luu y: Co the mat vai giay de ngrok hoat dong va chap nhan ket noi.
echo.
REM Loại bỏ phần lấy link ngrok tự động và mở trình duyệt
REM Doan code duoi day da bi loai bo:
REM set "url="
REM for /f "tokens=2 delims=: " %%a in ('curl -s http://127.0.0.1:4040/api/tunnels ^| findstr /i "public_url"') do (
REM     set "url=%%a"
REM )
REM set "url=%url:~2,-2%"
REM if "%url%"=="" (
REM     echo [ERROR] Khong lay duoc link Ngrok.
REM     pause
REM     goto exit
REM )
REM echo [INFO] Mo trinh duyet: %url%
REM start "" "%url%"

goto exit

:start_ollama_only
REM Chạy Ollama trong một cửa sổ riêng
start "Ollama Server" cmd /k "ollama serve"
echo [INFO] Ollama da duoc khoi dong. Ban co the mo cac ung dung khac.
goto exit

:exit
echo [INFO] Tat ca cac dich vu da duoc khoi dong hoac tat.
pause
exit