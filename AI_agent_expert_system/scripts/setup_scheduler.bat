@echo off
chcp 65001 >nul
title AI Expert System - 排程任務自動設定
echo ============================================================
echo  AI Expert System - Windows Task Scheduler 排程設定
echo ============================================================
echo.

:: 檢查管理員權限
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [錯誤] 請以管理員身份執行此腳本！
    echo 右鍵點擊此檔案 → 以系統管理員身分執行
    pause
    exit /b 1
)

REM 取得專案絕對路徑 (去掉結尾斜線)
set "PROJECT=%~dp0.."
for %%I in ("%PROJECT%") do set "PROJECT=%%~fI"

echo 專案路徑: %PROJECT%
echo.

:: 確保備份目錄存在
if not exist "%PROJECT%\backend\data\backups" mkdir "%PROJECT%\backend\data\backups"
if not exist "%PROJECT%\logs" mkdir "%PROJECT%\logs"

echo [1/3] 設定自動清理任務 (每天 02:00)...
schtasks /create /tn "AIExpert-Cleanup" ^
  /tr "python \"%PROJECT%\scripts\cleanup.py\" --all" ^
  /sc daily /st 02:00 /ru SYSTEM /rl HIGHEST /f
if %errorLevel% equ 0 (
    echo   [OK] AIExpert-Cleanup 已建立
) else (
    echo   [失敗] 建立失敗，請檢查 Python 路徑
)

echo.
echo [2/3] 設定 Chat DB 備份 (每 6 小時)...
schtasks /create /tn "AIExpert-Backup-Chat" ^
  /tr "\"%PROJECT%\scripts\backup_db.bat\"" ^
  /sc hourly /mo 6 /ru SYSTEM /rl HIGHEST /f
if %errorLevel% equ 0 (
    echo   [OK] AIExpert-Backup-Chat 已建立
) else (
    echo   [失敗] 建立失敗
)

echo.
echo [3/3] 設定 Token DB 備份 (每天 03:00)...
schtasks /create /tn "AIExpert-Backup-Token" ^
  /tr "cmd /c copy \"%PROJECT%\backend\data\documents\tokenrecord_v2.db\" \"%PROJECT%\backend\data\backups\tokenrecord_v2_backup.db\"" ^
  /sc daily /st 03:00 /ru SYSTEM /f
if %errorLevel% equ 0 (
    echo   [OK] AIExpert-Backup-Token 已建立
) else (
    echo   [失敗] 建立失敗
)

echo.
echo ============================================================
echo  設定完成！目前已建立的排程任務:
echo ============================================================
echo.
schtasks /query /fo TABLE | findstr "AIExpert"
echo.
echo 管理指令:
echo   查看: schtasks /query /tn "AIExpert-Cleanup" /fo LIST
echo   手動: schtasks /run /tn "AIExpert-Cleanup"
echo   刪除: schtasks /delete /tn "AIExpert-Cleanup" /f
echo.
pause
