@echo off
chcp 65001 >nul
echo ============================================
echo    AI Expert System v2.0 - 全部啟動
echo ============================================
echo.

cd /d "%~dp0\.."

REM 檢查 .env
if not exist ".env" (
    echo [WARN] .env 不存在，從 .env.example 複製...
    if exist ".env.example" copy .env.example .env
)

REM 檢查虛擬環境
if exist "venv\Scripts\activate.bat" (
    echo [INFO] 啟動虛擬環境...
    call venv\Scripts\activate.bat
)

REM 安裝依賴
echo [INFO] 安裝依賴...
pip install -r backend\requirements.txt -q
pip install -r frontend\requirements.txt -q

REM 初始化資料庫
echo [INFO] 初始化資料庫...
python scripts\init_db.py

REM 啟動後端 (背景)
echo.
echo [INFO] 啟動 FastAPI 後端 (背景)...
start "AI Expert - Backend" cmd /c "uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload"

REM 等待後端就緒
echo [INFO] 等待後端啟動...
timeout /t 3 /nobreak >nul

REM 啟動前端
@echo off
REM Get Network IP using Python (reliable)
for /f "delims=" %%I in ('python -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('8.8.8.8', 80)); print(s.getsockname()[0]); s.close()"') do set NETWORK_IP=%%I

echo [INFO] 啟動 Streamlit 前端...
echo.
echo ============================================
echo    後端 API : http://localhost:8000/docs
echo    前端 (本機): http://localhost:8501
echo    前端 (區網): http://%NETWORK_IP%:8501
echo ============================================
echo.
streamlit run frontend\Home.py --server.port 8501 --server.address %NETWORK_IP%

pause
