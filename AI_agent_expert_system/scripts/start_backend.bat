@echo off
chcp 65001 >nul
echo ============================================
echo    AI Expert System - 啟動後端 (FastAPI)
echo ============================================
echo.

cd /d "%~dp0\.."

REM 檢查 .env
if not exist ".env" (
    echo [WARN] .env 不存在，從 .env.example 複製...
    if exist ".env.example" (
        copy .env.example .env
        echo [INFO] 請修改 .env 中的 API Key 等設定
    ) else (
        echo [ERROR] .env.example 也不存在，請先建立環境設定檔
        pause
        exit /b 1
    )
)

REM 檢查虛擬環境
if exist "venv\Scripts\activate.bat" (
    echo [INFO] 啟動虛擬環境...
    call venv\Scripts\activate.bat
) else (
    echo [WARN] 未偵測到虛擬環境 (venv)
)

REM 安裝依賴
echo [INFO] 檢查後端依賴...
pip install -r backend\requirements.txt -q

REM 初始化資料庫
echo [INFO] 初始化資料庫...
python scripts\init_db.py

REM 啟動 FastAPI
echo.
echo [INFO] 啟動 FastAPI 後端...
echo [INFO] API 文件: http://localhost:8000/docs
echo [INFO] 健康檢查: http://localhost:8000/health
echo.
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

pause
