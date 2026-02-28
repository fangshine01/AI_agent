@echo off
chcp 950 >nul
echo ============================================
echo    AI Expert System - Start Frontend (Local)
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

echo.
echo [INFO] Starting Chat app (localhost only)...
echo [INFO] Local : http://localhost:8501
echo.
streamlit run frontend\chat_app.py --server.port 8501 --server.address localhost
pause
