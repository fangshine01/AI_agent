@echo off
chcp 950 >nul
echo ============================================
echo   AI Expert System - Stop All Services
echo ============================================
echo.
echo [1/2] Stopping backend (uvicorn)...
taskkill /FI "WINDOWTITLE eq AI Expert Backend*" /T /F >nul 2>&1
taskkill /IM uvicorn.exe /F >nul 2>&1

echo [2/2] Stopping frontend (streamlit)...
taskkill /FI "WINDOWTITLE eq AI Expert Frontend*" /T /F >nul 2>&1
taskkill /IM streamlit.exe /F >nul 2>&1

echo.
echo [OK] All services stopped.
echo.
pause
