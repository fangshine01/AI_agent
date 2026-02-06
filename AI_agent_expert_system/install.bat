@echo off
chcp 65001 >nul
echo ========================================
echo AI PPT 專家系統 - 安裝依賴套件
echo ========================================
echo.

echo [1/2] 檢查 Python 版本...
python --version
if %errorlevel% neq 0 (
    echo ❌ 錯誤: 找不到 Python！
    echo 請確認已安裝 Python 3.10 或更新版本
    pause
    exit /b 1
)
echo.

echo [2/2] 安裝 requirements.txt 中的套件...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo ✅ 安裝完成！
    echo ========================================
    echo.
    echo 下一步:
    echo 1. 複製 .env.example 為 .env
    echo 2. 編輯 .env 檔案，填入 API Key
    echo 3. 執行 run.bat 啟動系統
    echo.
) else (
    echo.
    echo ❌ 安裝過程中發生錯誤
    echo 請檢查錯誤訊息並重試
    echo.
)

pause
