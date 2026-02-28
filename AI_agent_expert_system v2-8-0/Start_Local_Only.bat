@echo off
chcp 950 >nul
echo ============================================
echo   AI Expert System - Start All (Local Only)
echo   Backend  : localhost:8000
echo   Chat     : localhost:8501
echo   Admin    : localhost:8502
echo ============================================
echo.
echo [1/3] Starting FastAPI backend (localhost)...
start "AI Expert Backend (Local)" cmd /k "scripts\start_backend_local.bat"

echo [2/3] Starting Chat app (localhost, port 8501)...
start "AI Expert Chat (Local)" cmd /k "scripts\start_chat_local.bat"

echo [3/3] Starting Admin+Stats app (localhost, port 8502)...
start "AI Expert Admin (Local)" cmd /k "scripts\start_admin_local.bat"

echo.
echo ============================================
echo   Services starting up...
echo   Backend  : http://localhost:8000/docs
echo   Chat     : http://localhost:8501
echo   Admin    : http://localhost:8502
echo   (Localhost only, not LAN accessible)
echo ============================================
echo.
echo Do NOT close the popup windows.
echo Press any key to close this window...
pause >nul
