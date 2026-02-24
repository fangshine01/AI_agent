@echo off
chcp 950 >nul
echo ============================================
echo   AI Expert System - Start (Local Only)
echo ============================================
echo.
echo [1/2] Starting FastAPI backend (local)...
start "AI Expert Backend (Local)" cmd /k "scripts\start_backend_local.bat"

echo [2/2] Starting Streamlit frontend (local)...
start "AI Expert Frontend (Local)" cmd /k "scripts\start_frontend_local.bat"

echo.
echo ============================================
echo   Services starting up...
echo   Backend  : http://localhost:8000/docs
echo   Frontend : http://localhost:8501
echo ============================================
echo.
echo Do NOT close the popup windows.
echo Press any key to close this window...
pause >nul
