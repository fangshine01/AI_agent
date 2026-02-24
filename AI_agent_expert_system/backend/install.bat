@echo off
chcp 950 >nul
echo ========================================
echo  AI Expert System - Install Dependencies
echo ========================================
echo.

echo [1/4] Checking Python version...
python --version
if %errorlevel% neq 0 goto :no_python
echo [OK] Python found.
echo.
goto :upgrade_pip

:no_python
echo [ERROR] Python not found!
echo Please install Python 3.10+ from https://www.python.org/downloads/
pause
exit /b 1

:upgrade_pip
echo [2/4] Upgrading pip...
python -m pip install --upgrade pip
echo.

echo [3/4] Installing backend dependencies...
python -m pip install -r requirements.txt
if %errorlevel% neq 0 goto :backend_fail
echo [OK] Backend packages installed.
echo.
goto :install_frontend

:backend_fail
echo [ERROR] Backend install failed.
echo  - Check your network connection
echo  - sqlite-vec needs Visual C++ Build Tools:
echo    https://visualstudio.microsoft.com/visual-cpp-build-tools/
pause
exit /b 1

:install_frontend
echo [4/4] Installing frontend dependencies...
python -m pip install -r ..\frontend\requirements.txt
if %errorlevel% neq 0 goto :frontend_warn
echo [OK] Frontend packages installed.
goto :done

:frontend_warn
echo [WARN] Frontend install had issues.
echo Run manually: pip install -r frontend\requirements.txt

:done
echo.
echo ========================================
echo  Installation complete!
echo ========================================
echo.
echo Next steps:
echo  1. Edit backend\.env and fill in your API keys
echo  2. Run Start_Local_Only.bat to start the system
echo.
pause
