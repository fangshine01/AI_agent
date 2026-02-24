@echo off
chcp 950 >nul
echo ============================================
echo   AI Expert System - Mixed Mode
echo   Frontend : LAN accessible
echo   Backend  : Localhost only
echo ============================================
echo.
echo [1/2] Starting FastAPI backend (localhost)...
start "AI Expert Backend (Local)" cmd /k "scripts\start_backend_local.bat"

echo [2/2] Starting Streamlit frontend (LAN)...
start "AI Expert Frontend (LAN)" cmd /k "scripts\start_frontend.bat"

echo.
echo ============================================
echo   Services starting up...
echo   Backend  : http://localhost:8000/docs (local only)
echo   Frontend : Check frontend window for Network URL
echo ============================================
echo.
echo Do NOT close the popup windows.
echo Press any key to close this window...
pause >nul
