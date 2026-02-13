@echo off
chcp 65001 >nul 2>&1
REM ============================================
REM   AI Expert System v2.2.0 - 停止所有服務
REM ============================================

echo ============================================
echo   停止 AI Expert System 所有服務
echo ============================================
echo.

REM 關閉 uvicorn (後端)
echo [1/2] 停止後端 API Server...
taskkill /FI "WINDOWTITLE eq AI Expert v2.2 - Backend API*" /T /F >nul 2>&1
taskkill /IM uvicorn.exe /F >nul 2>&1

REM 關閉 streamlit (前端)
echo [2/2] 停止前端介面...
taskkill /FI "WINDOWTITLE eq AI Expert v2.2 - Frontend*" /T /F >nul 2>&1

echo.
echo [OK] 所有服務已停止
echo.
pause
