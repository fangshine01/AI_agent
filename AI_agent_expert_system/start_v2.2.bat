@echo off
chcp 65001 >nul 2>&1
REM ============================================
REM   AI Expert System v2.2.0 - 完整啟動腳本
REM   後端 (FastAPI:8000) + 前端 (Streamlit:8501)
REM ============================================

echo ============================================
echo   AI Expert System v2.2.0
echo   Windows 原生部署啟動腳本
echo ============================================
echo.

REM 設定工作目錄為腳本所在位置
cd /d "%~dp0"

REM --- 檢查 Python ---
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [錯誤] 找不到 Python，請先安裝 Python 3.10+
    pause
    exit /b 1
)
echo [OK] Python 已安裝
echo.

REM --- 檢查 .env ---
if not exist ".env" (
    echo [警告] 未偵測到 .env 檔案
    if exist ".env.example" (
        copy .env.example .env >nul
        echo [INFO] 已從 .env.example 複製建立 .env
        echo [INFO] 請編輯 .env 填入必要設定
    ) else (
        echo [警告] 未找到 .env.example，請手動建立 .env 檔案
    )
    echo.
)

REM --- 自動安裝依賴（首次使用時） ---
if not exist ".deps_installed_v2.2" (
    echo [0/3] 首次使用 v2.2.0，正在安裝依賴...
    echo.
    echo [0.1] 安裝根目錄依賴...
    pip install -r requirements.txt -q
    echo [0.2] 安裝後端依賴（含 slowapi）...
    pip install -r backend\requirements.txt -q
    echo [0.3] 安裝前端依賴...
    if exist "frontend\requirements.txt" pip install -r frontend\requirements.txt -q
    echo. > .deps_installed_v2.2
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
echo [OK] 資料目錄已就緒
echo.

REM --- 啟動後端 API Server (Port 8000) ---
echo [1/2] 啟動後端 API Server (Port 8000)...
start "AI Expert v2.2 - Backend API" cmd /k "cd /d %~dp0 && set PYTHONPATH=%~dp0 && python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload"

REM 等待後端啟動
echo      等待後端就緒 (5 秒)...
timeout /t 5 /nobreak >nul

REM 驗證後端是否啟動
curl -s http://localhost:8000/health >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] 後端 API 已啟動
) else (
    echo [警告] 後端可能尚未完全就緒，繼續啟動前端...
)
echo.

REM --- 啟動前端 UI (Port 8501) ---
echo [2/2] 啟動前端介面 (Port 8501)...
start "AI Expert v2.2 - Frontend" cmd /k "cd /d %~dp0 && set PYTHONPATH=%~dp0 && streamlit run frontend/Home.py --server.port 8501 --server.address 0.0.0.0 --server.headless true --server.enableXsrfProtection false"

echo.
echo ============================================
echo   啟動完成！
echo ============================================
echo.
echo   後端 API:    http://localhost:8000
echo   API 文件:    http://localhost:8000/docs
echo   前端介面:    http://localhost:8501
echo   健康檢查:    http://localhost:8000/health
echo   詳細狀態:    http://localhost:8000/health/detailed
echo.
echo   如需關閉，請關閉各個終端視窗
echo   或執行 stop_all.bat
echo ============================================
echo.
pause
