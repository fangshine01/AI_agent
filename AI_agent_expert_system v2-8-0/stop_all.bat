@echo off
chcp 950 >nul
echo ============================================
echo   AI Expert System - Stop All Services
echo ============================================
echo.
echo [1/3] Stopping backend (uvicorn)...
taskkill /FI "WINDOWTITLE eq AI Expert Backend*" /T /F >nul 2>&1
taskkill /IM uvicorn.exe /F >nul 2>&1

echo [2/3] Stopping Chat app (streamlit :8501)...
taskkill /FI "WINDOWTITLE eq AI Expert Chat*" /T /F >nul 2>&1

echo [3/3] Stopping Admin app (streamlit :8502)...
taskkill /FI "WINDOWTITLE eq AI Expert Admin*" /T /F >nul 2>&1

echo [+]   Stopping all remaining streamlit processes...
taskkill /IM streamlit.exe /F >nul 2>&1

echo.
echo [OK] All services stopped.
echo.
pause
