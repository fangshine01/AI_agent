@echo off
chcp 65001 >nul
title AI Expert System - NSSM 服務安裝工具
echo ============================================================
echo  AI Expert System - Windows 服務安裝 (NSSM)
echo ============================================================
echo.
echo 此腳本將使用 NSSM 將 Backend 和 Chat UI 註冊為 Windows 服務，
echo 實現開機自動啟動、自動重啟等功能。
echo.
echo 前置條件:
echo  1. 已安裝 NSSM (https://nssm.cc/download)
echo  2. NSSM 已加入 PATH 或放在本目錄下
echo  3. 已安裝 Python 並配置虛擬環境
echo.

:: 檢查管理員權限
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [錯誤] 請以管理員身份執行此腳本！
    echo 右鍵點擊此檔案 → 以系統管理員身分執行
    pause
    exit /b 1
)

:: 設定路徑變數
set "PROJECT_ROOT=%~dp0.."
set "BACKEND_DIR=%PROJECT_ROOT%\backend"
set "FRONTEND_DIR=%PROJECT_ROOT%\frontend"
set "VENV_PYTHON=%PROJECT_ROOT%\.venv\Scripts\python.exe"
set "LOG_DIR=%PROJECT_ROOT%\logs"

:: 確認 NSSM 存在
where nssm >nul 2>&1
if %errorLevel% neq 0 (
    if exist "%~dp0nssm.exe" (
        set "NSSM=%~dp0nssm.exe"
    ) else (
        echo [錯誤] 找不到 NSSM，請先安裝:
        echo   下載: https://nssm.cc/download
        echo   解壓後將 nssm.exe 放入 PATH 或此腳本同目錄
        pause
        exit /b 1
    )
) else (
    set "NSSM=nssm"
)

:: 確認 Python 虛擬環境
if not exist "%VENV_PYTHON%" (
    echo [警告] 未找到虛擬環境: %VENV_PYTHON%
    echo 嘗試使用系統 Python...
    where python >nul 2>&1
    if %errorLevel% neq 0 (
        echo [錯誤] 找不到 Python，請先安裝
        pause
        exit /b 1
    )
    set "VENV_PYTHON=python"
)

:: 建立日誌目錄
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo.
echo ============================================================
echo  選擇操作:
echo ============================================================
echo.
echo  [1] 安裝所有服務 (Backend + Chat UI + Admin UI)
echo  [2] 僅安裝 Backend 服務
echo  [3] 僅安裝 Chat UI 服務
echo  [4] 僅安裝 Admin UI 服務
echo  [5] 移除所有服務
echo  [6] 查看服務狀態
echo  [7] 重新啟動所有服務
echo  [0] 離開
echo.
set /p choice="請選擇 (0-7): "

if "%choice%"=="1" goto :install_all
if "%choice%"=="2" goto :install_backend
if "%choice%"=="3" goto :install_chat
if "%choice%"=="4" goto :install_admin
if "%choice%"=="5" goto :remove_all
if "%choice%"=="6" goto :status
if "%choice%"=="7" goto :restart_all
if "%choice%"=="0" goto :exit
echo [錯誤] 無效選擇
goto :exit

:: ========== 安裝 Backend ==========
:install_backend
echo.
echo [安裝] Backend API 服務...

%NSSM% install AIExpert-Backend "%VENV_PYTHON%" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
%NSSM% set AIExpert-Backend AppDirectory "%BACKEND_DIR%"
%NSSM% set AIExpert-Backend DisplayName "AI Expert System - Backend API"
%NSSM% set AIExpert-Backend Description "AI Expert System FastAPI 後端服務 (Port 8000)"
%NSSM% set AIExpert-Backend Start SERVICE_AUTO_START
%NSSM% set AIExpert-Backend AppStdout "%LOG_DIR%\backend_stdout.log"
%NSSM% set AIExpert-Backend AppStderr "%LOG_DIR%\backend_stderr.log"
%NSSM% set AIExpert-Backend AppRotateFiles 1
%NSSM% set AIExpert-Backend AppRotateBytes 52428800
%NSSM% set AIExpert-Backend AppRotateOnline 1
%NSSM% set AIExpert-Backend AppRestartDelay 5000
%NSSM% set AIExpert-Backend AppThrottle 10000

echo [完成] Backend 服務已安裝
goto :eof

:: ========== 安裝 Chat UI ==========
:install_chat
echo.
echo [安裝] Chat UI 服務...

%NSSM% install AIExpert-ChatUI "%VENV_PYTHON%" -m streamlit run pages/1_💬_Chat.py --server.port 8501 --server.headless true
%NSSM% set AIExpert-ChatUI AppDirectory "%FRONTEND_DIR%"
%NSSM% set AIExpert-ChatUI DisplayName "AI Expert System - Chat UI"
%NSSM% set AIExpert-ChatUI Description "AI Expert System Streamlit 聊天介面 (Port 8501)"
%NSSM% set AIExpert-ChatUI Start SERVICE_AUTO_START
%NSSM% set AIExpert-ChatUI AppStdout "%LOG_DIR%\chat_ui_stdout.log"
%NSSM% set AIExpert-ChatUI AppStderr "%LOG_DIR%\chat_ui_stderr.log"
%NSSM% set AIExpert-ChatUI AppRotateFiles 1
%NSSM% set AIExpert-ChatUI AppRotateBytes 52428800
%NSSM% set AIExpert-ChatUI AppRotateOnline 1
%NSSM% set AIExpert-ChatUI AppRestartDelay 5000
%NSSM% set AIExpert-ChatUI DependOnService AIExpert-Backend

echo [完成] Chat UI 服務已安裝 (依賴 Backend)
goto :eof

:: ========== 安裝 Admin UI ==========
:install_admin
echo.
echo [安裝] Admin UI 服務...

%NSSM% install AIExpert-AdminUI "%VENV_PYTHON%" -m streamlit run pages/2_📁_Admin.py --server.port 8502 --server.headless true
%NSSM% set AIExpert-AdminUI AppDirectory "%FRONTEND_DIR%"
%NSSM% set AIExpert-AdminUI DisplayName "AI Expert System - Admin UI"
%NSSM% set AIExpert-AdminUI Description "AI Expert System Streamlit 管理介面 (Port 8502)"
%NSSM% set AIExpert-AdminUI Start SERVICE_AUTO_START
%NSSM% set AIExpert-AdminUI AppStdout "%LOG_DIR%\admin_ui_stdout.log"
%NSSM% set AIExpert-AdminUI AppStderr "%LOG_DIR%\admin_ui_stderr.log"
%NSSM% set AIExpert-AdminUI AppRotateFiles 1
%NSSM% set AIExpert-AdminUI AppRotateBytes 52428800
%NSSM% set AIExpert-AdminUI AppRotateOnline 1
%NSSM% set AIExpert-AdminUI AppRestartDelay 5000
%NSSM% set AIExpert-AdminUI DependOnService AIExpert-Backend

echo [完成] Admin UI 服務已安裝 (依賴 Backend)
goto :eof

:: ========== 安裝全部 ==========
:install_all
call :install_backend
call :install_chat
call :install_admin
echo.
echo ============================================================
echo  所有服務已安裝完成！
echo ============================================================
echo  啟動服務: net start AIExpert-Backend
echo  啟動服務: net start AIExpert-ChatUI
echo  啟動服務: net start AIExpert-AdminUI
echo ============================================================

:: 詢問是否立即啟動
echo.
set /p start_now="是否立即啟動所有服務? (y/n): "
if /i "%start_now%"=="y" (
    net start AIExpert-Backend
    timeout /t 3 /nobreak >nul
    net start AIExpert-ChatUI
    net start AIExpert-AdminUI
    echo 所有服務已啟動！
)
goto :exit

:: ========== 移除全部 ==========
:remove_all
echo.
echo [移除] 停止並移除所有 AI Expert 服務...

%NSSM% stop AIExpert-AdminUI >nul 2>&1
%NSSM% stop AIExpert-ChatUI >nul 2>&1
%NSSM% stop AIExpert-Backend >nul 2>&1

%NSSM% remove AIExpert-AdminUI confirm >nul 2>&1
%NSSM% remove AIExpert-ChatUI confirm >nul 2>&1
%NSSM% remove AIExpert-Backend confirm >nul 2>&1

echo [完成] 所有服務已移除
goto :exit

:: ========== 查看狀態 ==========
:status
echo.
echo ============================================================
echo  服務狀態:
echo ============================================================
echo.
echo --- Backend ---
%NSSM% status AIExpert-Backend 2>nul || echo   (未安裝)
echo.
echo --- Chat UI ---
%NSSM% status AIExpert-ChatUI 2>nul || echo   (未安裝)
echo.
echo --- Admin UI ---
%NSSM% status AIExpert-AdminUI 2>nul || echo   (未安裝)
echo.
goto :exit

:: ========== 重啟全部 ==========
:restart_all
echo.
echo [重啟] 重新啟動所有服務...
%NSSM% restart AIExpert-AdminUI >nul 2>&1
%NSSM% restart AIExpert-ChatUI >nul 2>&1
%NSSM% restart AIExpert-Backend >nul 2>&1
echo [完成] 所有服務已重新啟動
goto :exit

:exit
echo.
pause
