@echo off
REM ##########################################################################
REM # File Batch để khởi chạy Trợ lý AI Cá nhân                             #
REM ##########################################################################

REM --- Thiết lập các biến ---
SET "PROJECT_DIR=%~dp0"
SET "PYTHON_VENV=%PROJECT_DIR%venv\Scripts\activate.bat"
SET "STREAMLIT_APP=%PROJECT_DIR%app.py"

REM --- Hiển thị menu cho người dùng ---
:menu
cls
echo ==========================================================
echo           KHOI DONG TRO LY AI CA NHAN
echo ==========================================================
echo.
echo  Chon mot tuy chon:
echo.
echo    1. Khoi dong Ollama Server & Tro ly AI (Streamlit)
echo    2. Chi khoi dong Tro ly AI (gia su Ollama da chay)
echo    3. Chi khoi dong Ollama Server
echo    4. Thoat
echo.
set /p choice="Nhap lua chon cua ban (1, 2, 3, 4): "

if "%choice%"=="1" goto start_all
if "%choice%"=="2" goto start_assistant_only
if "%choice%"=="3" goto start_ollama_only
if "%choice%"=="4" goto exit
goto menu

REM --- Chức năng 1: Khởi động cả hai ---
:start_all
echo [INFO] Dang khoi dong Ollama Server trong mot cua so moi...
start "Ollama Server" cmd /k "ollama serve"
echo [INFO] Doi 5 giay de Ollama Server khoi dong...
timeout /t 5 /nobreak > nul
goto start_assistant_only

REM --- Chức năng 2: Chỉ khởi động Trợ lý AI ---
:start_assistant_only
echo [INFO] Dang kich hoat moi truong ao Python...
call "%PYTHON_VENV%"

if not exist "%PYTHON_VENV%" (
    echo [ERROR] Khong tim thay moi truong ao tai: %PYTHON_VENV%
    echo [ERROR] Vui long chay 'python -m venv venv' truoc.
    pause
    goto exit
)

echo [INFO] Dang khoi dong ung dung Streamlit...
start "Personal AI Assistant" streamlit run "%STREAMLIT_APP%"
goto exit

REM --- Chức năng 3: Chỉ khởi động Ollama Server ---
:start_ollama_only
echo [INFO] Dang khoi dong Ollama Server trong mot cua so moi...
start "Ollama Server" cmd /k "ollama serve"
goto exit


REM --- Thoát chương trình ---
:exit
echo [INFO] Hoan tat. Ban co the dong cua so nay.
exit