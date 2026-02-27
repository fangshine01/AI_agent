# AI Expert System v2.2.0 — 部署與使用指南

> 適用環境: Windows 10 Pro / Windows Server 2019+  
> 最後更新: 2026-02-13

---

## 目錄

1. [系統需求](#1-系統需求)
2. [快速部署](#2-快速部署)
3. [服務架構](#3-服務架構)
4. [資料庫說明](#4-資料庫說明)
5. [模型清單](#5-模型清單)
6. [使用者操作指南](#6-使用者操作指南)
7. [管理員操作指南](#7-管理員操作指南)
8. [排程任務設定](#8-排程任務設定)
9. [備份與恢復](#9-備份與恢復)
10. [故障排除](#10-故障排除)

---

## 1. 系統需求

| 項目 | 最低配置 | 推薦配置 |
|------|---------|---------|
| **CPU** | 4 Core | 8 Core |
| **RAM** | 8 GB | 16 GB |
| **磁碟** | 100 GB | 500 GB+ (Chat History 永久保留) |
| **OS** | Windows 10 Pro | Windows Server 2022 |
| **Python** | 3.10+ | 3.11+ |
| **網路** | 100 Mbps | 1 Gbps |

### 必要軟體

```
Python 3.10+
pip (附帶於 Python)
uvicorn (pip install)
streamlit (pip install)
```

---

## 2. 快速部署

### 2.1 首次安裝

```bat
cd D:\Github\AI_agent\AI_agent_expert_system

REM 1. 建立虛擬環境 (建議)
python -m venv venv
call venv\Scripts\activate

REM 2. 安裝依賴
pip install -r backend\requirements.txt
pip install -r frontend\requirements.txt
pip install -r requirements.txt

REM 3. 複製並編輯環境設定
copy .env.example .env
notepad .env

REM 4. 一鍵啟動
start_v2.2.bat
```

### 2.2 日常啟動

```bat
start_v2.2.bat
```

啟動後可存取:
- **後端 API**: http://localhost:8000/docs
- **Chat UI**: http://localhost:8501
- **Admin UI**: http://localhost:8501 → 左側選單「📁 Admin」

### 2.3 停止服務

```bat
stop_all.bat
```

---

## 3. 服務架構

```
┌───────────────────────────────────────────────┐
│                  使用者端                       │
│  ┌──────────┐         ┌──────────┐            │
│  │ Chat UI  │         │ Admin UI │            │
│  │ :8501    │         │ :8501    │            │
│  └────┬─────┘         └────┬─────┘            │
│       │  HTTP (X-API-Key)  │                  │
│       └──────────┬─────────┘                  │
│                  ▼                             │
│  ┌──────────────────────────────┐             │
│  │     Backend API (:8000)      │             │
│  │  FastAPI + uvicorn           │             │
│  └──────┬───────────┬───────────┘             │
│         │           │                          │
│    ┌────▼────┐  ┌───▼────────┐               │
│    │ SQLite  │  │ Enterprise │               │
│    │ WAL DB  │  │ API Proxy  │               │
│    └─────────┘  └────────────┘               │
└───────────────────────────────────────────────┘
```

| 服務 | Port | 說明 |
|------|------|------|
| Backend API | 8000 | 核心邏輯、DB、Token 統計、AI 處理 |
| Chat UI | 8501 | Streamlit Multi-Page App (一般用戶) |
| Admin UI | 8501 | 同上，透過頁面選單進入管理介面 |

### 身份識別 (BYOK)

用戶在前端輸入 API Key，即為身份識別依據：
- `user_id = SHA256(API_Key + Username)[:16]`
- 共用 Key 時需填寫 Username 區分

---

## 4. 資料庫說明

所有資料庫位於: `backend/data/documents/`

| 資料庫 | 用途 | 備份頻率 |
|--------|------|---------|
| `knowledge_v2.db` | 知識庫、Chat 歷史、Session | 每 6 小時 |
| `tokenrecord_v2.db` | Token 使用統計 | 每日 |

> ⚠️ 所有元件均讀取同一份資料庫（backend/data/documents/），**不存在 v1/v2 分裂問題**。

### WAL 模式

資料庫已啟用 WAL (Write-Ahead Logging)，支援高併發讀寫：
- 50~100 人同時在線無鎖定衝突
- `PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;`

---

## 5. 模型清單

企業 API Proxy 同時支援 OpenAI 與 Gemini，透過相同端點呼叫：

| 顯示名稱 | API Model ID | 分類 |
|----------|-------------|------|
| GPT-4.1 | `gpt-4.1-preview` | Default High-end |
| GPT-4.1-mini | `gpt-4.1-mini-preview` | Default Fast |
| GPT-4o | `gpt-4o` | Standard |
| GPT-4o-mini | `gpt-4o-mini` | Standard Fast |
| gemini-2.5-pro | `gemini-2.5-pro` | Google High-end |
| gemini-2.5-flash | `gemini-2.5-flash` | Google Fast |
| gemini-2.5-flash-Lite | `gemini-2.5-flash-lite` | Google Lite |
| GPT-5.1 | `gpt-5.1-preview` | Future |
| GPT-5-mini | `gpt-5-mini-preview` | Future |
| gemini 3.0 Pro Preview | `gemini-3.0-pro-preview` | Future |
| gemini 3.0 Pro flash Preview | `gemini-3.0-flash-preview` | Future |
| gemini 2.5 flash image | `gemini-2.5-flash-nano-banana` | Image Optimized |
| gemini 3.0 Pro image Preview | `gemini-3.0-pro-nano-banana` | Image Optimized |

> 模型清單在 `backend/config.py` 的 `AVAILABLE_MODELS` 中定義，可隨時新增或移除。

---

## 6. 使用者操作指南

### 6.1 首次連線

1. 開啟 http://localhost:8501
2. 左側 **🔑 連線** Tab:
   - 選擇 API 提供者
   - 輸入 API Key
   - (選填) 輸入使用者名稱
   - 點擊「🔐 驗證 API Key」
3. 驗證成功後，下方出現**模型選擇器**（13 個模型可選）

### 6.2 問答對話

1. 從側邊欄選擇問答模型
2. 在主畫面輸入問題
3. 系統自動搜尋知識庫 → AI 生成回答
4. 支援查詢模式: 一般搜尋、異常解析、SOP 手順、技術規格、培訓教材

### 6.3 對話歷史

- **📜 歷史** Tab: 查看過去的對話 Session
- 點擊 Session 可載入歷史對話
- Chat History **永久保留**，不自動刪除

### 6.4 個人資料管理 (GDPR)

管理員可在 Admin UI 的「系統健康」頁面：
- **匯出** 個人對話記錄 (JSON)
- **查看** 個人統計
- **刪除** 所有個人資料（不可復原）

---

## 7. 管理員操作指南

### 7.1 進入 Admin

1. 開啟 http://localhost:8501
2. 左側選單選擇「📁 Admin」
3. 輸入 Admin API Key 並驗證

### 7.2 功能概覽

| Tab | 說明 |
|-----|------|
| 📁 文件管理 | 上傳/刪除知識文件 |
| 📊 Token 統計 | 查看使用量圖表（每日/模型/用戶/時段） |
| 🔧 系統設定 | 調整 API 參數 |
| 💚 系統健康 | 健康狀態、GDPR 資料管理 |

---

## 8. 排程任務設定

### 一鍵安裝排程任務

```bat
scripts\setup_scheduler.bat
```

此腳本會建立:
- **AIExpert-Cleanup**: 每日 02:00 清理過期 Session
- **AIExpert-Backup-Chat**: 每 6 小時備份 Chat History
- **AIExpert-Backup-Token**: 每日 03:00 備份 Token DB

### 手動管理

```bat
REM 查詢排程狀態
schtasks /query /tn "AIExpert-Cleanup"

REM 手動觸發
schtasks /run /tn "AIExpert-Backup-Chat"

REM 刪除排程
schtasks /delete /tn "AIExpert-Cleanup" /f
```

詳細說明請參考 [docs/scheduler.md](scheduler.md)。

---

## 9. 備份與恢復

### 9.1 手動備份

```bat
scripts\backup_db.bat
```

備份位置: `backend/data/backups/`

### 9.2 備份恢復驗證

```bat
python scripts\test_backup_recovery.py
```

此腳本會:
1. 自動找到最新備份
2. 複製到臨時目錄恢復
3. 執行 `PRAGMA integrity_check`
4. 比較與正式 DB 的差異
5. 清理臨時檔案

### 9.3 資料遷移 (v1 → v2)

若有舊版本 `data/knowledge.db` 需遷移：

```bat
REM 檢查遷移狀態
python scripts\migrate_v1_to_v2.py --check

REM 執行遷移
python scripts\migrate_v1_to_v2.py --migrate
```

---

## 10. 故障排除

| 問題 | 可能原因 | 解決方式 |
|------|---------|---------|
| 前端無法連線後端 | Backend 未啟動 | 檢查 http://localhost:8000/health |
| API Key 驗證失敗 | Key 無效或網路問題 | 檢查 Key 是否正確、proxy 是否可達 |
| database is locked | 多重寫入衝突 | 確認 WAL 模式已啟用 |
| 模型下拉空白 | 驗證未完成 | 先完成 API Key 驗證 |
| Token 統計無資料 | DB 路徑不一致 | 確認 config.py DB 路徑 |
| 排程未執行 | Task Scheduler 未設定 | 執行 `scripts\setup_scheduler.bat` |

### 日誌位置

| 日誌 | 路徑 |
|------|------|
| Backend | `backend/data/logs/backend.log` |
| Cleanup | `logs/cleanup.log` |
| 應用 | `data/logs/app.log` |

### 健康檢查 API

```
GET http://localhost:8000/health          # 基本健康檢查
GET http://localhost:8000/health/detailed  # 詳細健康報告
```
