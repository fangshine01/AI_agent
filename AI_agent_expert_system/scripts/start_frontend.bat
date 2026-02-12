@echo off
chcp 65001 >nul
echo ============================================
echo    AI Expert System - 啟動前端 (Streamlit)
echo ============================================
echo.

cd /d "%~dp0\.."

REM 檢查虛擬環境
if exist "venv\Scripts\activate.bat" (
    echo [INFO] 啟動虛擬環境...
    call venv\Scripts\activate.bat
)

REM 安裝依賴
echo [INFO] 檢查前端依賴...
pip install -r frontend\requirements.txt -q

REM 啟動 Streamlit
echo.
@echo off
REM Get Network IP using Python (reliable)
for /f "delims=" %%I in ('python -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('8.8.8.8', 80)); print(s.getsockname()[0]); s.close()"') do set NETWORK_IP=%%I

echo [INFO] 啟動 Streamlit 前端...
echo [INFO] 本機網址: http://localhost:8501
echo [INFO] 區域網路網址 (Network IP): http://%NETWORK_IP%:8501
echo.
streamlit run frontend\Home.py --server.port 8501 --server.address %NETWORK_IP%

pause
