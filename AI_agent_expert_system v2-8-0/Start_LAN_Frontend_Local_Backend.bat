@echo off
chcp 950 >nul
echo ============================================
echo   AI Expert System - Chat LAN + Admin/Backend Local
echo   Chat     : LAN 0.0.0.0:8501
echo   Admin    : localhost:8502
echo   Backend  : localhost:8000
echo ============================================
echo.
echo [1/3] Starting FastAPI backend (localhost)...
start "AI Expert Backend (Local)" cmd /k "scripts\start_backend_local.bat"

echo [2/3] Starting Chat app (LAN, port 8501)...
start "AI Expert Chat (LAN)" cmd /k "scripts\start_frontend.bat"

echo [3/3] Starting Admin+Stats app (localhost, port 8502)...
start "AI Expert Admin (Local)" cmd /k "scripts\start_admin_local.bat"

echo.
echo ============================================
echo   Services starting up...
echo   Backend  : http://localhost:8000/docs
echo   Chat     : Check Chat window for Network URL
echo   Admin    : http://localhost:8502
echo ============================================
echo.
echo Do NOT close the popup windows.
echo Press any key to close this window...
pause >nul
