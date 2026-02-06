@echo off
REM AI Expert System v2.0 - 雙 UI 啟動腳本
echo ========================================
echo AI Expert System v2.0 啟動中...
echo ========================================
echo.

REM 檢查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [錯誤] 找不到 Python，請先安裝 Python 3.8+
    pause
    exit /b 1
)

echo [1/2] 啟動管理後台 (Port 8501)...
start "Admin UI" cmd /k "streamlit run admin_app.py --server.port 8501"

echo [2/2] 啟動問答介面 (Port 8502)...
start "Chat UI" cmd /k "streamlit run chat_app.py --server.port 8502"

echo.
echo ========================================
echo 啟動完成！
echo ========================================
echo.
REM echo 管理後台: http://localhost:8501
REM echo 問答介面: http://localhost:8502
echo.
echo 按任意鍵關閉本視窗...
pause >nul
