@echo off
chcp 65001 >nul 2>&1
REM ============================================
REM   AI Expert System - 防火牆設定腳本
REM   功能: 僅允許局域網存取，阻擋外網
REM ============================================

echo ============================================
echo   AI Expert System - 防火牆安全設定
echo ============================================
echo.
echo   此腳本將建立 Windows 防火牆規則，確保：
echo   ✅ 局域網內電腦可以連接 (192.168.x.x)
echo   ❌ 外網無法存取你的服務
echo.
echo   Port 8501 (Streamlit 前端)
echo   Port 8000 (FastAPI 後端)
echo.
pause

REM 檢查系統管理員權限
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [錯誤] 需要系統管理員權限！
    echo.
    echo 請以「系統管理員身分執行」此腳本：
    echo   1. 右鍵點擊此檔案
    echo   2. 選擇「以系統管理員身分執行」
    echo.
    pause
    exit /b 1
)

echo.
echo [1/4] 正在建立防火牆規則...

REM 刪除舊規則（如果存在）
netsh advfirewall firewall delete rule name="AI-Expert-Streamlit-LAN" >nul 2>&1
netsh advfirewall firewall delete rule name="AI-Expert-FastAPI-LAN" >nul 2>&1

REM 建立新規則 - Streamlit (Port 8501)
echo [2/4] 設定 Streamlit 前端 (Port 8501)...
netsh advfirewall firewall add rule ^
    name="AI-Expert-Streamlit-LAN" ^
    dir=in ^
    action=allow ^
    protocol=TCP ^
    localport=8501 ^
    remoteip=192.168.0.0/16,10.0.0.0/8,172.16.0.0/12 ^
    profile=private ^
    description="AI Expert System 前端 - 僅限局域網存取"

if %errorlevel% equ 0 (
    echo [OK] Streamlit 規則建立成功
) else (
    echo [錯誤] Streamlit 規則建立失敗
)

REM 建立新規則 - FastAPI (Port 8000)
echo [3/4] 設定 FastAPI 後端 (Port 8000)...
netsh advfirewall firewall add rule ^
    name="AI-Expert-FastAPI-LAN" ^
    dir=in ^
    action=allow ^
    protocol=TCP ^
    localport=8000 ^
    remoteip=192.168.0.0/16,10.0.0.0/8,172.16.0.0/12 ^
    profile=private ^
    description="AI Expert System 後端 - 僅限局域網存取"

if %errorlevel% equ 0 (
    echo [OK] FastAPI 規則建立成功
) else (
    echo [錯誤] FastAPI 規則建立失敗
)

REM 顯示建立的規則
echo.
echo [4/4] 驗證防火牆規則...
echo.
netsh advfirewall firewall show rule name="AI-Expert-Streamlit-LAN" | findstr /C:"規則名稱" /C:"Rule Name" /C:"啟用" /C:"Enabled" /C:"動作" /C:"Action"
echo.
netsh advfirewall firewall show rule name="AI-Expert-FastAPI-LAN" | findstr /C:"規則名稱" /C:"Rule Name" /C:"啟用" /C:"Enabled" /C:"動作" /C:"Action"

echo.
echo ============================================
echo   防火牆設定完成！
echo ============================================
echo.
echo   已建立規則:
echo   ✅ AI-Expert-Streamlit-LAN (Port 8501)
echo   ✅ AI-Expert-FastAPI-LAN (Port 8000)
echo.
echo   允許連接的 IP 範圍:
echo   - 192.168.0.0 ~ 192.168.255.255
echo   - 10.0.0.0 ~ 10.255.255.255
echo   - 172.16.0.0 ~ 172.31.255.255
echo.
echo   [安全提示]
echo   ✅ 同網段電腦可以連接
echo   ❌ 外網無法存取（需確保路由器未開放 Port）
echo.
echo   [驗證步驟]
echo   1. 執行 scripts\start_backend.bat 與 scripts\start_frontend.bat 啟動服務
echo   2. 從局域網其他電腦測試連接（應該成功）
echo   3. 使用手機 4G 網路測試（應該失敗）
echo.
echo   [移除規則]
echo   如需移除防火牆規則，請執行以下命令：
echo   netsh advfirewall firewall delete rule name="AI-Expert-Streamlit-LAN"
echo   netsh advfirewall firewall delete rule name="AI-Expert-FastAPI-LAN"
echo.
echo ============================================
echo.
pause
