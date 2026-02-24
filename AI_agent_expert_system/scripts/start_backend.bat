@echo off
chcp 950 >nul
echo ============================================
echo    AI Expert System - Start Backend (LAN)
echo ============================================
echo.

cd /d "%~dp0\.."

if not exist "backend\.env" goto :no_env
goto :check_venv

:no_env
echo [WARN] backend\.env not found
if not exist "backend\.env.example" goto :no_example
copy "backend\.env.example" "backend\.env"
echo [INFO] Copied .env.example to .env
goto :check_venv

:no_example
echo [ERROR] backend\.env.example missing, please create it first
pause
exit /b 1

:check_venv
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
echo [INFO] Checking backend dependencies...
pip install -r backend\requirements.txt -q

echo.
echo [INFO] Starting FastAPI backend (0.0.0.0)...
echo [INFO] API Docs : http://localhost:8000/docs
echo [INFO] Health   : http://localhost:8000/health
echo.
cd /d "%~dp0\..\backend"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause
