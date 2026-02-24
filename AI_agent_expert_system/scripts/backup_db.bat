@echo off
chcp 65001 >nul 2>&1
REM ============================================
REM   SQLite 資料庫備份腳本
REM   可搭配 Windows 工作排程器定時執行
REM ============================================

echo [備份] 開始備份 SQLite 資料庫...

REM 切換到專案根目錄
cd /d "%~dp0\.."

REM 設定備份目錄
set "DB_DIR=backend\data\documents"
set "BACKUP_DIR=backend\data\backups"

REM 取得時間戳記 (格式: YYYYMMDD_HHMM)
set "DT=%date:~0,4%%date:~5,2%%date:~8,2%"
set "TM=%time:~0,2%%time:~3,2%"
set "TM=%TM: =0%"
set "TIMESTAMP=%DT%_%TM%"

if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

REM 備份 knowledge_v2.db
if exist "%DB_DIR%\knowledge_v2.db" (
    echo [1/2] 備份 knowledge_v2.db...
    copy "%DB_DIR%\knowledge_v2.db" "%BACKUP_DIR%\knowledge_v2_%TIMESTAMP%.db" >nul
    echo [OK] knowledge_v2.db 備份完成
) else (
    echo [跳過] knowledge_v2.db 不存在
)

REM 備份 tokenrecord_v2.db
if exist "%DB_DIR%\tokenrecord_v2.db" (
    echo [2/2] 備份 tokenrecord_v2.db...
    copy "%DB_DIR%\tokenrecord_v2.db" "%BACKUP_DIR%\tokenrecord_v2_%TIMESTAMP%.db" >nul
    echo [OK] tokenrecord_v2.db 備份完成
) else (
    echo [跳過] tokenrecord_v2.db 不存在
)

REM 清理超過 30 天的備份
echo [清理] 刪除 30 天前的舊備份...
forfiles /p "%BACKUP_DIR%" /s /m *.db /d -30 /c "cmd /c del @path" >nul 2>&1

echo.
echo [完成] 資料庫備份作業結束
echo 備份位置: %BACKUP_DIR%
