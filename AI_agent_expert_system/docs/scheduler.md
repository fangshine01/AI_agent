# Windows Task Scheduler 排程設定指南

> 本文件說明如何在 Windows 環境中設定自動化排程任務，包含定時清理、備份、健康檢查等。

## 1. 前置條件

- Windows 10 Pro / Windows Server 2019+
- Python 已安裝且加入 PATH
- 專案位於 `D:\Github\AI_agent\AI_agent_expert_system`

## 2. 排程任務總覽

| 任務名稱 | 排程時間 | 說明 |
|---|---|---|
| AIExpert-Cleanup | 每天 02:00 | 清理過期 Session / 上傳 / 日誌 / VACUUM |
| AIExpert-Backup-Chat | 每 6 小時 | 備份 knowledge_v2.db（含 Chat History） |
| AIExpert-Backup-Token | 每 24 小時 | 備份 tokenrecord_v2.db |

---

## 3. 設定步驟

### 3.1 自動清理任務

**使用命令列建立：**

```bat
schtasks /create ^
  /tn "AIExpert-Cleanup" ^
  /tr "python D:\Github\AI_agent\AI_agent_expert_system\scripts\cleanup.py --all" ^
  /sc daily ^
  /st 02:00 ^
  /ru SYSTEM ^
  /rl HIGHEST ^
  /f
```

**驗證已建立：**

```bat
schtasks /query /tn "AIExpert-Cleanup" /fo LIST
```

**手動觸發測試：**

```bat
schtasks /run /tn "AIExpert-Cleanup"
```

### 3.2 Chat History 備份（每 6 小時）

```bat
schtasks /create ^
  /tn "AIExpert-Backup-Chat" ^
  /tr "D:\Github\AI_agent\AI_agent_expert_system\scripts\backup_db.bat" ^
  /sc hourly ^
  /mo 6 ^
  /ru SYSTEM ^
  /rl HIGHEST ^
  /f
```

### 3.3 Token DB 備份（每天）

```bat
schtasks /create ^
  /tn "AIExpert-Backup-Token" ^
  /tr "powershell -Command \"Copy-Item 'D:\Github\AI_agent\AI_agent_expert_system\backend\data\documents\tokenrecord_v2.db' 'D:\Github\AI_agent\AI_agent_expert_system\backend\data\backups\tokenrecord_v2_%DATE:~0,4%%DATE:~5,2%%DATE:~8,2%.db'\"" ^
  /sc daily ^
  /st 03:00 ^
  /ru SYSTEM ^
  /f
```

---

## 4. 使用 GUI 設定（替代方案）

若偏好圖形介面：

1. 按 `Win + R` → 輸入 `taskschd.msc` → Enter
2. 右側面板點選「建立基本工作」
3. 依照精靈填入：
   - **名稱**：`AIExpert-Cleanup`
   - **觸發程序**：每天、02:00
   - **動作**：啟動程式
   - **程式/指令碼**：`python`
   - **新增引數**：`D:\Github\AI_agent\AI_agent_expert_system\scripts\cleanup.py --all`
   - **起始位置**：`D:\Github\AI_agent\AI_agent_expert_system`
4. 完成後，右鍵 → 屬性 → 勾選「以最高權限執行」

---

## 5. 管理與監控

### 查看所有 AIExpert 排程

```bat
schtasks /query /fo TABLE | findstr "AIExpert"
```

### 刪除排程

```bat
schtasks /delete /tn "AIExpert-Cleanup" /f
schtasks /delete /tn "AIExpert-Backup-Chat" /f
schtasks /delete /tn "AIExpert-Backup-Token" /f
```

### 檢查執行紀錄

清理任務的執行紀錄會寫入：
- `logs/cleanup.log`（腳本自身日誌）
- Windows 事件檢視器 → 應用程式與服務記錄檔 → Microsoft → Windows → TaskScheduler

---

## 6. 故障排除

| 問題 | 可能原因 | 解決方式 |
|---|---|---|
| 任務不執行 | Python 不在 PATH | 改用完整路徑：`C:\Python312\python.exe` |
| 權限不足 | 未以 SYSTEM 或管理員執行 | 加 `/ru SYSTEM /rl HIGHEST` |
| 腳本找不到模組 | PYTHONPATH 未設定 | 在 .bat 中先 `set PYTHONPATH=D:\Github\AI_agent\AI_agent_expert_system` |
| 資料庫鎖定 | 備份時 Backend 在寫入 | 先執行 `PRAGMA wal_checkpoint(FULL)` |

---

## 7. 一鍵設定腳本

將以下內容儲存為 `scripts/setup_scheduler.bat`，以管理員身份執行即可自動建立所有排程：

```bat
@echo off
chcp 65001 >nul
echo ============================================
echo  AI Expert System - 排程任務自動設定
echo ============================================

set PROJECT=D:\Github\AI_agent\AI_agent_expert_system

:: 清理任務 - 每天 02:00
schtasks /create /tn "AIExpert-Cleanup" ^
  /tr "python %PROJECT%\scripts\cleanup.py --all" ^
  /sc daily /st 02:00 /ru SYSTEM /rl HIGHEST /f

:: Chat DB 備份 - 每 6 小時
schtasks /create /tn "AIExpert-Backup-Chat" ^
  /tr "%PROJECT%\scripts\backup_db.bat" ^
  /sc hourly /mo 6 /ru SYSTEM /rl HIGHEST /f

echo.
echo ✅ 所有排程任務已設定完成
echo 使用 schtasks /query /fo TABLE | findstr "AIExpert" 查看
pause
```
