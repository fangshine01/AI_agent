@echo off
chcp 950 >nul
echo ============================================
echo    AI Expert System - Start Admin App (LAN)
echo ============================================
echo.

cd /d "%~dp0\.."

if exist ".venv\Scripts\activate.bat" goto :use_venv1
if exist "venv\Scripts\activate.bat" goto :use_venv2
echo [WARN] No virtual environment found, using system Python
goto :install_deps

:use_venv1
call ".venv\Scripts\activate.bat"
goto :install_deps

:use_venv2
call "venv\Scripts\activate.bat"
goto :install_deps

:install_deps
echo [INFO] Checking frontend dependencies...
pip install -r frontend\requirements.txt -q

for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /C:"IPv4"') do (
    set RAW_IP=%%A
    goto :got_ip
)
:got_ip
set NETWORK_IP=%RAW_IP: =%

echo.
echo [INFO] Starting Admin+Stats app on port 8502 (LAN accessible)...
echo [INFO] Local   : http://localhost:8502
echo [INFO] Network : http://%NETWORK_IP%:8502
echo.
streamlit run frontend\admin_app.py --server.port 8502 --server.address 0.0.0.0
pause
