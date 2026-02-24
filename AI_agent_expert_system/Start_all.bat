@echo off
chcp 950 >nul
echo ============================================
echo   AI Expert System - Start All Services
echo ============================================
echo.
echo [1/2] Starting FastAPI backend...
start "AI Expert Backend" cmd /k "scripts\start_backend.bat"

echo [2/2] Starting Streamlit frontend...
start "AI Expert Frontend" cmd /k "scripts\start_frontend.bat"

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
