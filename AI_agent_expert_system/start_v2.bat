@echo off
chcp 65001 >nul 2>&1
REM ============================================
REM   AI Expert System v2.0 - 啟動腳本
REM   後端 (FastAPI) + 前端 (Streamlit)
REM ============================================

echo ============================================
echo   AI Expert System v2.0
echo ============================================
echo.

REM 設定工作目錄為腳本所在位置
cd /d "%~dp0"

REM --- 檢查 Python ---
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [錯誤] 找不到 Python，請先安裝 Python 3.8+
    pause
    exit /b 1
)

echo [OK] Python 已安裝
echo.

REM --- 自動安裝依賴（首次使用時） ---
if not exist ".deps_installed" (
    echo [0/2] 首次使用，正在安裝後端依賴...
    pip install -r backend\requirements.txt -q
    echo [0/2] 正在安裝前端依賴...
    pip install -r frontend\requirements.txt -q
    echo. > .deps_installed
    echo [OK] 所有依賴安裝完成
    echo.
)

REM --- 確保資料目錄存在 ---
if not exist "data" mkdir data
if not exist "backend\data\documents" mkdir backend\data\documents
if not exist "backend\data\raw_files" mkdir backend\data\raw_files
if not exist "backend\data\archived_files" mkdir backend\data\archived_files
if not exist "backend\data\generated_md" mkdir backend\data\generated_md
if not exist "backend\data\failed_files" mkdir backend\data\failed_files

REM --- 啟動後端 API Server (Port 8000) ---
echo [1/2] 啟動後端 API Server (Port 8000)...
start "AI Expert - Backend API" cmd /k "cd /d %~dp0 && set PYTHONPATH=%~dp0 && python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload"

REM 等待後端啟動
echo      等待後端就緒...
timeout /t 4 /nobreak >nul

REM --- 啟動前端 UI (Port 8501) ---
echo [2/2] 啟動前端介面 (Port 8501)...
start "AI Expert - Frontend" cmd /k "cd /d %~dp0 && set PYTHONPATH=%~dp0 && streamlit run frontend/Home.py --server.port 8501 --server.address 0.0.0.0 --server.headless true --server.enableXsrfProtection false"

echo.
echo ============================================
echo   啟動完成！
echo ============================================
echo.
echo   [本機存取]
echo   前端介面:       http://localhost:8501
echo   後端 API:       http://localhost:8000
echo   API 文件:       http://localhost:8000/docs
echo.
echo   頁面功能:
echo     - 專家問答:   Chat 頁面
echo     - 管理後台:   Admin 頁面
echo     - 統計儀表:   Stats 頁面
echo.
echo   [安全提示]
echo   - 僅接受本機存取: 使用 localhost 連接
echo   - 外部連線: 需使用正確的 IP 位址 (不會自動顯示)
echo.
echo   資料庫: 首次啟動時自動建立
echo   檔案監控: 後端啟動後自動開啟
echo.
echo   提示: 關閉各服務視窗即可停止對應服務
echo ============================================
echo.
pause
