@echo off
chcp 950 >nul
echo ============================================
echo   AI Expert System - Start All (Full LAN)
echo   Backend  : LAN 0.0.0.0:8000
echo   Chat     : LAN 0.0.0.0:8501
echo   Admin    : LAN 0.0.0.0:8502
echo ============================================
echo.
echo [1/3] Starting FastAPI backend (LAN)...
start "AI Expert Backend (LAN)" cmd /k "scripts\start_backend.bat"

echo [2/3] Starting Chat app (LAN, port 8501)...
start "AI Expert Chat (LAN)" cmd /k "scripts\start_frontend.bat"

echo [3/3] Starting Admin+Stats app (LAN, port 8502)...
start "AI Expert Admin (LAN)" cmd /k "scripts\start_admin.bat"

echo.
echo ============================================
echo   Services starting up...
echo   Backend  : http://localhost:8000/docs
echo   Chat     : http://localhost:8501
echo   Admin    : http://localhost:8502
echo   (All accessible from LAN)
echo ============================================
echo.
echo Do NOT close the popup windows.
echo Press any key to close this window...
pause >nul
