# [Phase 2] 長期優化與架構重構執行計畫 (Final Detailed Execution Plan)(v2-1-0 版本)

> [!IMPORTANT]
> **適用對象**: 外部開發者 Agent (External Developer Agent)
> **目標**: 實作高併發、前後端分離、具備使用者記憶的企業級系統。
> **規模**: 支援 50~100 人同時在線 (High Concurrency)。
> **核心原則**: **Backend is the Single Source of Truth**. 前端 (Port 8501/8502) 禁止直接讀取 DB。

## 1. 架構定義 (Architecture Definition)

### 1.1 服務拓樸
| 服務 (Service) | Port | 職責 (Role) | 存取權限 | 用戶識別 (Identity) |
|---|---|---|---|---|
| **Backend API** | **8000** | 核心邏輯、DB 存取、Token 統計、AI 處理 | ✅ RW (Owner) | **GPT API Key** (Dual Purpose) |
| **Chat UI** | **8501** | 一般用戶問答介面 | ❌ API Only | User 輸入 GPT Key |
| **Admin UI** | **8502** | 管理員儀表板、檔案上傳、報表 | ❌ API Only | Admin 輸入 Admin Key |

### 1.2 用戶識別策略 (Identity Strategy - BYOK)
採用 **"User GPT API Key = User Identity"** 的模式。
- **機制**: 用戶在前端輸入的 OpenAI/Gemini Key，直接作為 `X-API-Key` Header 發送給後端。
- **雙重用途**:
    1.  **連線驗證**: 後端接收 Key，將其 **Hash** 後視為 `user_id`，用於存取 History DB。
    2.  **模型呼叫**: 後端使用原始 Key 呼叫 LLM (OpenAI/Google)。
- **衝突警告 (Crucial Warning)**:
    > [!CAUTION]
    > **共用 Key 問題**: 若多個用戶共用同一個 API Key (例如部門共用公帳 Key)，他們將會**看到彼此的對話歷史**。
    > **解決方案**: 建議 UI 增加一個選填的 "Username" 欄位，若有填寫，則 `user_id = Hash(API Key + Username)`，確保共用 Key 也能區分個人。

### 1.3 高併發策略 (Concurrency Strategy)
針對 50~100 人同時在線，SQLite 需進行特定優化，否則會遇到 `database is locked`。
- [ ] **資料庫優化**: 必須啟用 **WAL Mode** (Write-Ahead Logging)。
    - SQL Command: `PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;`
    - 實作位置: `backend/app/utils/db_init.py` 與 `core/database/connection.py`。
- [ ] **連線管理**: Backend API 需確保每個 Request 使用獨立的 DB Connection (或使用 Connection Pool)，不可共用全域 Connection。
- [ ] **非同步處理**: 所有 IO 操作 (AI 呼叫、DB 讀寫) 必須使用 `async/await`，避免阻塞 Event Loop。

---

## 2. 資料庫變更 (Database Schema Changes)
**Target**: `backend/app/utils/db_init.py`
新增對話歷史記錄表，以支援「用戶記憶」。

```sql
-- 新增表: chat_history
CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,        -- Hash(API_Key) OR Hash(API_Key + Username)
    session_id TEXT NOT NULL,     -- 對話 Session ID
    role TEXT NOT NULL,           -- 'user' | 'assistant'
    content TEXT NOT NULL,        -- 訊息內容
    model_used TEXT,              -- 使用的模型
    tokens_used INTEGER,          -- 該次訊息消耗 Token
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_chat_history_user ON chat_history(user_id);
CREATE INDEX idx_chat_history_session ON chat_history(session_id);
```

---

### Step 0: 安全驗證機制 (Security & Validation) - **[NEW]**
**Target**: `backend/app/api/v1/auth.py`

1.  **新增驗證 Endpoint (`/auth/verify`)**:
    *   **目的**: 在用戶進入系統前，先確認 API Key 有效，防止無效 Key 消耗後端資源或攻擊 DB。
    *   **方法**: 接收 Frontend 傳來的 Key，後端輕量呼叫外部 API 測試。
    *   **策略**: 推薦使用 **`GET /models`** (List Models) 或 **`POST /embeddings`**。
        *   **List Models**: 完全免費，速度快，適合僅驗證 Key 有效性。
        *   **Embeddings**: 消耗極少 Token，可驗證 Key 是否具備模型調用權限 (User 建議)。
    *   **流程**:
        1.  Frontend: 用戶輸入 Key -> 點擊 "連線"。
        2.  Frontend -> Backend: `POST /auth/verify { key: "..." }`。
        3.  Backend -> OpenAI/Google: 呼叫對應 API (List Models or Embeddings)。
        4.  If Success: Backend 回傳 `{ status: "ok", user_hash: "..." }`。
        5.  Frontend: 顯示 Chat 介面。
        6.  If Fail: 顯示錯誤訊息，**禁止進入主畫面**。

### Step 1: 後端核心升級 (Backend Upgrade)
**Target**: `backend/`

1.  **啟用 WAL 模式**:
    *   在 `db_init.py` 的 `_init_knowledge_db` 與 `_init_token_db` 函數最後，執行 `PRAGMA journal_mode=WAL;`。
2.  **實作 Identity Middleware**:
    *   接收 Header `X-API-Key` 與 `X-User-Name` (Optional)。
    *   生成 `request.state.user_id`。
    *   **重要**: 原始 Key 僅在需要呼叫 LLM 時解密/使用，DB 僅存 Hash。
3.  **實作 Chat History API**:
    *   新增 `backend/app/api/v1/history.py`。
    *   權限: 僅允許讀取 `request.state.user_id` 及其名下的 Sessions。
    *   `GET /history/sessions`: 取得該用戶的所有對話。
    *   `POST /chat/query`: 完成後寫入歷史。

### Step 2: Chat UI 重構 (Port 8501)
**Target**: `chat_app.py` -> **Refactor 為 `frontend/chat_interface.py`** (建議改名以區分)

1.  **移除本地 DB 依賴**: 
    *   **Strict Rule**: 搜尋整個檔案，刪除所有 `import core.*`。
2.  **API Client 整合**:
    *   UI 初始化與登入頁面:
        *   輸入框 [API Key] (Required)
        *   輸入框 [Username] (Optional - 提示: "若共用 Key 請輸入名稱以區分歷史")
    *   將 Key 與 Username 存入 `st.session_state` 與 `APIClient`。
3.  **UI 佈局優化**:
    *   **左側 Sidebar**: 
        *   **Model 選擇器**: 依據 User 指定支援以下模型 (含 Future/Preview)。
            > **API Model ID 對照表 (Configurable in `backend/config.py`)**:
            
            | 顯示名稱 (Display Name) | API 模型 ID (Model ID) | 備註 |
            |---|---|---|
            | `GPT-4.1` | `gpt-4.1-preview` | Default High-end |
            | `GPT-4.1-mini` | `gpt-4.1-mini-preview` | Default Fast |
            | `GPT-4o` | `gpt-4o` | Standard |
            | `GPT-4o-mini` | `gpt-4o-mini` | Standard Fast |
            | `gemini-2.5-pro` | `gemini-2.5-pro` | Google High-end |
            | `gemini-2.5-flash` | `gemini-2.5-flash` | Google Fast |
            | `gemini-2.5-flash-Lite` | `gemini-2.5-flash-lite` | Google Lite |
            | `GPT-5.1` | `gpt-5.1-preview` | Future |
            | `GPT-5-mini` | `gpt-5-mini-preview` | Future |
            | `gemini 3.0 Pro Preview` | `gemini-3.0-pro-preview` | Future |
            | `gemini 3.0 Pro flash Preview` | `gemini-3.0-flash-preview` | Future |
            | `gemini 2.5 flash image(nano banana)` | `gemini-2.5-flash-nano-banana` | Image Optimized |
            | `gemini 3.0 Pro image Preview(nano banana pro)` | `gemini-3.0-pro-nano-banana` | Image Optimized |

        *   **歷史對話列表**: 呼叫 `/history/sessions` 顯示個人歷史。
    *   **右側 Main**: 
        *   對話視窗。
        *   圖片顯示支援: 若 API 回傳 `image_url`，使用 `st.image()` 渲染。

### Step 3: Admin UI 遷移 (Port 8502)
**Target**: `frontend/admin_dashboard.py` (New Entry Point)

1.  **整合既有頁面**:
    *   將 `frontend/pages/2_Admin.py` 與 `3_Stats.py` 功能整合。
2.  **Token 報表增強**:
    *   新增 "By User (Hash)" 統計視圖 (透過 user_id 分組)，觀察高用量用戶。
    *   新增 "By Hour" 圖表，監控高併發時段。
3.  **檔案管理**:
    *   修正原本無法顯示列表的問題 (改接 `/api/v1/admin/documents`)。

---

## 4. 啟動腳本 (Windows 原生部署)

### 4.1 標準啟動腳本
為支援 50~100 人，後端使用 `uvicorn` 單一 Process (Windows 下 SQLite WAL 模式，單一 Process + Async I/O 效能最佳，避免鎖定衝突)。

**`run_backend.bat`**:
```bat
@echo off
echo 🚀 啟動 Backend API Server (Port 8000)...
set PYTHONPATH=%cd%
:: Windows 下 SQLite 建議單一 Process 處理寫入，避免 Lock
:: --log-level info 減少大量 I/O
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --workers 1 --log-config logging.yaml
```

**`run_chat_ui.bat`**:
```bat
@echo off
echo 💬 啟動 Chat UI (Port 8501)...
set PYTHONPATH=%cd%
streamlit run frontend/chat_interface.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
```

**`run_admin_ui.bat`**:
```bat
@echo off
echo 🛠️ 啟動 Admin Dashboard (Port 8502)...
set PYTHONPATH=%cd%
streamlit run frontend/admin_dashboard.py --server.port 8502 --server.address 0.0.0.0 --server.headless true
```

**`run_all.bat`** (一鍵啟動):
```bat
@echo off
echo 📦 啟動完整系統 (Backend + Chat + Admin)...
start "Backend API" cmd /k run_backend.bat
timeout /t 5 /nobreak
start "Chat UI" cmd /k run_chat_ui.bat
start "Admin UI" cmd /k run_admin_ui.bat
echo ✅ 所有服務已啟動！
echo - Backend: http://localhost:8000/docs
echo - Chat UI: http://localhost:8501
echo - Admin UI: http://localhost:8502
pause
```

### 4.2 Windows 服務化 (可選)

**使用 NSSM (Non-Sucking Service Manager) 將應用註冊為 Windows 服務**:

```bat
:: 下載並安裝 NSSM
:: https://nssm.cc/download

:: 註冊 Backend 服務
nssm install AIAgentBackend "C:\Path\To\Python\python.exe" "-m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"
nssm set AIAgentBackend AppDirectory "D:\Github\AI_agent\AI_agent_expert_system"
nssm set AIAgentBackend DisplayName "AI Agent Backend API"
nssm set AIAgentBackend Description "AI Expert System Backend Service"
nssm start AIAgentBackend

:: 註冊 Chat UI 服務 (可選)
nssm install AIAgentChatUI "C:\Path\To\Python\Scripts\streamlit.exe" "run frontend/chat_interface.py --server.port 8501"
nssm set AIAgentChatUI AppDirectory "D:\Github\AI_agent\AI_agent_expert_system"
nssm start AIAgentChatUI
```

### 4.3 健康檢查端點 (Health Check)
**Target**: `backend/app/api/v1/health.py` (New)
```python
@router.get("/health")
async def health_check():
    """健康檢查，用於 Load Balancer 與 Monitoring"""
    checks = {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }
    
    # 檢查資料庫連線
    try:
        db = get_database()
        db.execute_query("SELECT 1")
        checks["services"]["database"] = "ok"
    except Exception as e:
        checks["services"]["database"] = f"error: {e}"
        checks["status"] = "degraded"
    
    # 檢查 LLM API (Optional, may slow down health check)
    # checks["services"]["openai"] = await test_openai_api()
    
    return JSONResponse(content=checks, status_code=200 if checks["status"] == "ok" else 503)
```

---

## 5. 錯誤處理與恢復機制 (Error Handling & Recovery)
**Target**: `backend/app/middleware/error_handler.py` (New)

### 5.1 統一錯誤處理
```python
# 實作全域 Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_id = uuid.uuid4()
    logger.error(f"[{error_id}] {type(exc).__name__}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "error_id": str(error_id)}
    )
```

### 5.2 重試機制 (Retry Logic)
- **LLM API 呼叫**: 使用 `tenacity` 套件，遇到 `RateLimitError` 或 `Timeout` 時自動重試 3 次（指數退避）。
- **資料庫寫入**: `OperationalError` (Locked) 時，等待 100ms 後重試，最多 5 次。

### 5.3 降級策略 (Graceful Degradation)
- 若知識庫搜尋失敗，回傳 "系統維護中，請稍後再試"，但不中斷服務。
- 若 LLM API 連續失敗 3 次，暫時回退至純知識檔檢索模式（不生成回答，僅返回相關文件片段）。

---

## 6. 監控、日誌與告警 (Monitoring & Alerting)
**Target**: `backend/app/middleware/monitoring.py` (New)

### 6.1 日誌管理
- **格式化日誌**: 採用 JSON 格式，包含 `timestamp`, `level`, `user_id_hash`, `endpoint`, `response_time`。
- **Log 輪轉**: 使用 `RotatingFileHandler`，每個 Log 檔案最大 50MB，保留最近 10 個檔案。
- **禁止記錄**: 原始 API Key、完整對話內容（僅記錄前 100 字元）。

### 6.2 性能監控
- **Prometheus Metrics**: 新增 `/metrics` 端點，暴露以下指標：
    - `http_request_duration_seconds`: 每個 Endpoint 回應時間。
    - `llm_api_calls_total`: LLM 呼叫次數與成功率。
    - `db_query_duration_seconds`: 資料庫查詢時間。
    - `active_users`: 當前活躍用戶數（基於 user_id）。

### 6.3 告警機制
- **條件觸發**:
    1. 單一用戶 1 分鐘內呼叫超過 30 次（潛在攻擊）。
    2. API 錯誤率 > 5%（過去 5 分鐘）。
    3. 資料庫回應時間 > 500ms（連續 10 次）。
- **通知方式**: 寫入專用 Log 檔案 (`alerts.log`)，並可選支援 Webhook（例如 Slack、Email）。

---

## 7. API 安全與限流 (Security & Rate Limiting)
**Target**: `backend/app/middleware/rate_limiter.py` (New)

### 7.1 Rate Limiting
- **每用戶配額**:
    - 一般用戶: **30 requests/min**, **500 requests/hour**。
    - Admin 用戶: **100 requests/min**, **2000 requests/hour**。
- **實作方式**: 使用 `slowapi` (基於 Flask-Limiter)，Key 為 `user_id_hash`。
- **超限回應**: 回傳 `HTTP 429 Too Many Requests` 及 `Retry-After` Header。

### 7.2 Input 驗證與 Sanitization
- **Query 長度限制**: 最多 2000 字元（防止超大 Prompt 攻擊）。
- **SQL Injection 防護**: 所有資料庫查詢使用 Parameterized Query，**絕不拼接字串**。
- **XSS 防護**: 前端顯示內容時，使用 `DOMPurify` 或 `bleach` 清理 HTML。

### 7.3 API Key 管理
- **加密儲存**: 若需暫存用戶的 API Key（例如 Session 期間），使用 `cryptography.fernet` 加密後存入 Redis。
- **定期清理**: Session 過期後（預設 24 小時），自動刪除加密 Key。

---

## 8. Session 管理與資料清理 (Session Management)
**Target**: `backend/app/utils/session_manager.py` (New)

### 8.1 Session 生命週期
- **建立時機**: 用戶首次通過 `/auth/verify` 後，產生 `session_id` (UUID)。
- **持續時間**: 預設 **24 小時**，可透過 `config.SESSION_TTL` 調整。
- **刷新機制**: 每次 API 呼叫時，自動延長 Session（最多延長至 7 天）。

### 8.2 自動清理策略
> [!NOTE]
> **已確認決策**: Chat History **永久保留**，不自動刪除。

- **定時任務**: 每日凌晨 2:00 執行 Windows Task Scheduler 觸發 `scripts/cleanup.py`，執行：
    1. 清理過期的 Session（超過 24 小時未活動）。
    2. 清理過期的臨時加密 Key（若有使用）。
    3. 清理超過 30 天的臨時上傳檔案（`data/temp_uploads/`）。
- **手動刪除**: Admin 可透過 `/admin/sessions/cleanup` 手動觸發清理。

**Windows Task Scheduler 設定**:
```bat
:: 建立定時任務（每日凌晨 2:00 執行清理）
schtasks /create /tn "AIAgentCleanup" /tr "C:\Path\To\Python\python.exe D:\Github\AI_agent\AI_agent_expert_system\scripts\cleanup.py" /sc daily /st 02:00
```

---

## 9. 測試與品質保證 (Testing & QA)
**Target**: `backend/tests/` & `frontend/tests/`

### 9.1 測試金字塔
| 層級 | 覆蓋率目標 | 工具 | 優先級 |
|---|---|---|---|
| **單元測試** (Unit Tests) | ≥ 80% | `pytest` | 🔴 必須 |
| **整合測試** (Integration Tests) | ≥ 60% | `pytest` + `TestClient` | 🟠 重要 |
| **E2E 測試** (End-to-End) | 關鍵流程 | `Playwright` or `Selenium` | 🟡 建議 |
| **壓力測試** (Load Tests) | 50~100 並發 | `Locust` | 🟢 上線前 |

### 9.2 關鍵測試案例
1.  **API Key 驗證**:
    - 測試無效 Key、過期 Key、空 Key 的錯誤處理。
2.  **並發寫入**:
    - 模擬 50 個用戶同時寫入 `chat_history`，驗證無 Deadlock。
3.  **Token 統計準確性**:
    - 對比 `openai.tiktoken` 與後端統計結果，誤差 < 5%。
4.  **Session 隔離**:
    - 測試兩個共用 Key 的用戶（但 Username 不同），確認看不到彼此的歷史。

### 9.3 壓力測試腳本
**`tests/load_test.py`**:
```python
from locust import HttpUser, task, between

class ChatUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # 模擬用戶登入
        response = self.client.post("/auth/verify", json={"key": "test_key"})
        self.user_hash = response.json()["user_hash"]
    
    @task
    def ask_question(self):
        self.client.post("/chat/query", json={
            "query": "這是測試問題",
            "api_key": "test_key"
        }, headers={"X-API-Key": self.user_hash})
```

執行: `locust -f tests/load_test.py --users 100 --spawn-rate 10`

---

## 10. 資料庫備份與災難恢復 (Backup & DR)
**Target**: `scripts/backup.py` (New)

### 10.1 自動備份策略
- **備份頻率**: 
    - `chat_history`: 每 **6 小時** 一次。
    - `knowledge v2.db`: 每 **12 小時** 一次。
    - `tokenrecord v2.db`: 每 **24 小時** 一次。
- **備份方式** (PowerShell): 
    ```powershell
    # WAL Mode 下，需先 Checkpoint
    sqlite3.exe knowledge_v2.db "PRAGMA wal_checkpoint(FULL);"
    
    # 建立備份 (帶時間戳)
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    Copy-Item "knowledge_v2.db" "backups\knowledge_v2_$timestamp.db"
    ```
- **保留政策**: 保留最近 **14 天**的備份，每月 1 號的備份永久保留。

**Windows Task Scheduler 設定範例**:
```bat
:: 每 6 小時備份 Chat History
schtasks /create /tn "BackupChatHistory" /tr "powershell.exe -File D:\Github\AI_agent\AI_agent_expert_system\scripts\backup_chat.ps1" /sc hourly /mo 6

:: 每 12 小時備份 Knowledge DB
schtasks /create /tn "BackupKnowledgeDB" /tr "powershell.exe -File D:\Github\AI_agent\AI_agent_expert_system\scripts\backup_knowledge.ps1" /sc hourly /mo 12
```

### 10.2 恢復測試
- **每週驗證**: 隨機選擇一個備份檔，嘗試恢復並執行查詢測試，確保備份可用。

---

## 11. API 文件與規範 (API Documentation)
**Target**: 自動生成 OpenAPI/Swagger 文件

### 11.1 文件生成
- FastAPI 自帶 Swagger UI: 存取 `http://localhost:8000/docs`。
- 確保所有 Endpoint 都有完整的:
    - `summary`: 簡短描述（中文）。
    - `description`: 詳細說明、參數範例。
    - `response_model`: 明確定義回傳結構。

### 11.2 版本控制
- API 路徑包含版本號: `/api/v1/...`、`/api/v2/...`。
- 向下相容 1 個 Major Version（例如 v2 上線後，v1 仍維持 6 個月）。

---

## 12. 部署前檢查清單 (Pre-Deployment Checklist)

### 12.1 環境配置
- [ ] `.env` 檔案已正確配置（不可提交至 Git）。
- [ ] `PYTHONPATH` 已設定。
- [ ] 所有目錄 (`data/`, `logs/`) 已建立並設定寫入權限。

### 12.2 性能驗證
- [ ] WAL Mode 已啟用 (`PRAGMA journal_mode;` 回傳 `wal`)。
- [ ] 執行壓力測試，確認 100 並發無 Error。
- [ ] API 平均回應時間 < 500ms（不含 LLM 呼叫時間）。

### 12.3 安全檢查
- [ ] Log 檔案中無原始 API Key。
- [ ] 所有 SQL 查詢使用 Parameterized Query。
- [ ] Rate Limiting 已啟用。

### 12.4 監控與告警
- [ ] Prometheus Metrics 可正常存取。
- [ ] 測試觸發一次告警（模擬高頻呼叫），確認 Log 記錄正確。

### 12.5 備份與恢復
- [ ] 自動備份腳本已加入 Windows Task Scheduler。
- [ ] 手動執行一次備份與恢復，驗證流程。
- [ ] 確認備份目錄 `backups/` 有足夠儲存空間（永久保留 Chat History）。

---

## 13. 版本升級路徑 (Migration from v1 to v2)
**Target**: `scripts/migrate_v1_to_v2.py` (New)

### 13.1 資料遷移
```python
# 將舊版 chat_history (如果存在) 轉移至新表
import sqlite3

src_db = sqlite3.connect("data/old_chat.db")
dst_db = sqlite3.connect("data/documents/knowledge_v2.db")

# 匯出舊資料，轉換 schema，匯入新 DB
# (需處理: user_id 從 username 改為 Hash(API Key))
```

### 13.2 配置同步
- 將舊 `config.py` 中的設定遷移至新的 `backend/config.py`。
- 確認所有環境變數 (`OPENAI_API_KEY`, `DB_PATH`) 對應正確。

### 13.3 並行運行期 (1~2 週)
- 新舊系統同時運行，逐步引導用戶切換至 v2。
- v2 先開放給內部測試用戶，收集回饋。

---

## 14. 配置管理與環境變數 (Configuration Management)
**Target**: `backend/config.py` + `.env.example` (New)

### 14.1 必要環境變數清單
```env
# API Keys
OPENAI_API_KEY=sk-xxxxx
OPENAI_BASE_URL=https://api.openai.com/v1
GEMINI_API_KEY=xxxxx

# Database Paths
DB_PATH=data/documents/knowledge_v2.db
TOKEN_DB_PATH=data/documents/tokenrecord_v2.db

# Security
SESSION_TTL=86400  # 24 hours
RATE_LIMIT_PER_MINUTE=30
RATE_LIMIT_PER_HOUR=500

# File Storage
RAW_FILES_DIR=data/raw_files
MAX_FILE_SIZE_MB=50

# Monitoring
ENABLE_METRICS=true
LOG_LEVEL=INFO
```

### 14.2 配置驗證
啟動時自動檢查關鍵配置是否缺失，若缺失則報錯並拒絕啟動：
```python
required_vars = ["OPENAI_API_KEY", "DB_PATH"]
missing = [v for v in required_vars if not os.getenv(v)]
if missing:
    raise RuntimeError(f"Missing environment variables: {missing}")
```

---

## 15. GDPR/資料隱私合規 (Data Privacy Compliance)

### 15.1 用戶資料導出
- **Endpoint**: `GET /user/export` (需 `X-API-Key` 驗證)。
- **回傳格式**: JSON，包含該用戶所有 `chat_history`、Token 統計、Session 記錄。

### 15.2 用戶資料刪除
- **Endpoint**: `DELETE /user/data` (需二次確認)。
- **操作**: 
    1. 刪除 `chat_history` 中該 `user_id` 的所有記錄。
    2. 刪除 Token 統計（或匿名化為 "Deleted User"）。
    3. Log 此操作，保留刪除時間與 Request IP（合規要求）。

### 15.3 資料保留政策通知
在 UI 顯眼位置（登入頁面）告知用戶：
> "您的對話記錄將永久保留在系統中。如需刪除個人資料，請聯繫管理員或使用「資料匯出/刪除」功能。"

---

## 16. 圖片處理增強 (Image Handling Enhancement)
**Target**: `backend/app/utils/image_processor.py` (Existing, to be enhanced)

### 16.1 自動壓縮與格式轉換
- **上傳時處理**:
    - 若圖片 > 2MB，自動壓縮至 < 2MB（使用 `Pillow`）。
    - 支援格式: `jpg`, `png`, `webp`。若上傳 `bmp` 或 `tiff`，自動轉為 `png`。
- **存儲路徑規劃**:
    ```
    data/images/
    ├── raw/          # 原始檔
    ├── compressed/   # 壓縮後
    └── thumbnails/   # 縮圖 (用於 Admin UI 列表)
    ```

### 16.2 圖片存取 API
- `GET /api/v1/images/{image_id}`: 回傳圖片（支援 `size` 參數: `raw`, `compressed`, `thumbnail`）。
- 前端使用: `st.image(f"http://localhost:8000/api/v1/images/{img_id}?size=compressed")`

---

## 17. Token 統計精確度提升 (Token Accounting Accuracy)
**Target**: `backend/app/middleware/token_tracker.py` (Existing, to be enhanced)

### 17.1 多模型支援
不同模型的 Token 計算方式不同，需分別處理：
```python
def count_tokens(text: str, model: str) -> int:
    if model.startswith("gpt-"):
        import tiktoken
        encoder = tiktoken.encoding_for_model(model)
        return len(encoder.encode(text))
    elif model.startswith("gemini"):
        # Google 模型使用 Byte Pair Encoding, 估算: 1 Token ≈ 4 Chars
        return len(text) // 4
    else:
        # 未知模型，保守估算
        return len(text) // 3
```

### 17.2 圖片 Token 計算
- **Vision 模型** (如 `gpt-4o`, `gemini-2.5-flash`) 處理圖片時，Token 消耗公式：
    - GPT-4o: `170 Tokens (base) + (width × height / 512) Tokens`
    - Gemini: 依解析度分級，詳見 [Google Pricing](https://ai.google.dev/pricing)

---

## 18. 開發者注意事項 (Developer Notes)
1.  **Conflict Warning**: 絕對禁止在前端 (`frontend/`) 使用 `sqlite3.connect()`。所有資料必須走 HTTP 8000。
2.  **Image Handling**: 圖片上傳後，後端需保留原始檔於 `data/raw_files` 或 `data/images`，並提供 API 供前端 `st.image()` 存取。
3.  **Privacy**: 確保在 Log 中**不要**印出原始的 API Key，僅記錄 Hash 或 Masked Key (`sk-****xxxx`)。
4.  **Async Best Practice**: 所有涉及 I/O 的函數 (DB, HTTP, File) 都必須是 `async def`，並使用 `await`。
5.  **錯誤處理**: 所有 API Endpoint 必須包在 `try-except` 中，並記錄 Error ID 方便追蹤。
6.  **測試覆蓋**: 每個新功能必須附帶至少 1 個整合測試，確保不破壞既有功能。

---

## 19. 實施時程與優先級規劃 (Implementation Timeline & Priorities)

### 19.1 優先級分級
| 優先級 | 代號 | 說明 | 時程 |
|---|---|---|---|
| **P0 - 阻斷性** | 🔴 | 不完成無法上線，核心功能 | Week 1-2 |
| **P1 - 重要** | 🟠 | 影響用戶體驗或系統穩定性 | Week 3-4 |
| **P2 - 建議** | 🟡 | 優化項目，可延後實施 | Week 5-6 |
| **P3 - 未來** | 🟢 | 長期優化，視需求實施 | After Launch |

### 19.2 四階段實施路線圖

#### ✅ Phase 1: 核心基礎設施 (Week 1-2) — **已完成**
**目標**: 完成基本架構，確保系統可運行

| 任務 | Target | 優先級 | 狀態 |
|---|---|---|---|
| 啟用 WAL Mode | `db_init.py` | P0 | ✅ 完成 |
| 實作 Identity Middleware | `middleware/auth.py` | P0 | ✅ 完成 |
| 新增 Chat History Schema | `db_init.py` | P0 | ✅ 完成 |
| 實作 Chat History API | `api/v1/history.py` | P0 | ✅ 完成 |
| 實作安全驗證 Endpoint | `api/v1/auth.py` | P0 | ✅ 完成 |
| Chat UI 移除本地 DB | `frontend/chat_interface.py` | P0 | ✅ 完成 |
| Chat UI API Client 整合 | `frontend/api_client.py` | P0 | ✅ 完成 |
| 基本錯誤處理 | `middleware/error_handler.py` | P0 | ✅ 完成 |
| 啟動腳本編寫 | `run_*.bat` | P0 | ✅ 完成 |
| 單元測試框架建立 | `tests/` | P0 | ✅ 完成 |
| **Phase 1 小計** | | | **62h (~8 工作天)** |

#### ✅ Phase 2: 性能與安全強化 (Week 3-4) — **已完成**
**目標**: 確保系統穩定、安全、高效

| 任務 | Target | 優先級 | 狀態 |
|---|---|---|---|
| Rate Limiting 實作 | `middleware/rate_limiter.py` | P1 | ✅ Phase 1 已完成 |
| 重試機制 (LLM + DB) | `utils/retry.py` | P1 | ✅ 完成 |
| Session 管理 | `utils/session_manager.py` | P1 | ✅ 完成 |
| Token 統計多模型支援 | `middleware/token_tracker.py` | P1 | ✅ 完成 |
| 日誌系統優化 | `utils/logger.py` | P1 | ✅ 完成 |
| Admin UI 整合與增強 | `frontend/pages/2_📁_Admin.py` | P1 | ✅ 完成 |
| Model 選擇器實作 | `frontend/pages/1_💬_Chat.py` | P1 | ✅ Phase 1 已完成 |
| 整合測試編寫 | `tests/load_test.py` | P1 | ✅ 完成 (Locust) |
| Input 驗證與 Sanitization | `middleware/validation.py` | P1 | ✅ 完成 |
| Config 驗證機制 | `config.py` | P1 | ✅ 完成 |
| GDPR 合規 (導出/刪除) | `api/v1/user.py` | P1 | ✅ 完成 |
| 自動清理定時任務 | `scripts/cleanup.py` | P1 | ✅ 完成 |
| NSSM 服務安裝腳本 | `scripts/setup_service.bat` | P1 | ✅ 完成 |

#### 🟡 Phase 3: 監控與進階優化 (Week 5-6) — **部分完成，其餘延至 Phase 5**
**目標**: 建立完整的監控、搜尋優化、E2E 測試

| 任務 | Target | 優先級 | 狀態 |
|---|---|---|---|
| Prometheus Metrics | `middleware/monitoring.py` | P2 | ⏳ 延至 Phase 5 |
| 搜尋最佳化 (向量索引) | `core/search.py` | P2 | ⏳ 延至 Phase 5 |
| E2E 測試 (Playwright) | `tests/e2e/` | P2 | ⏳ 延至 Phase 5 |
| API 文件完善 | `main.py` docstrings | P2 | ⏳ 延至 Phase 5 |
| Windows Task Scheduler 說明 | `docs/scheduler.md` | P2 | ✅ 完成 (含 deployment_guide.md) |
| **Phase 3 小計** | | | **40h (~5 工作天)** |

#### ✅ Phase 4: 部署與深度整合 (After Week 6) — **已完成**
**目標**: 正式上線準備、深度整合驗證、Legacy 清理

| 任務 | Target | 優先級 | 狀態 |
|---|---|---|---|
| Windows 服務化 (NSSM) | `setup_service.bat` | P2 | ✅ Phase 2 已完成 |
| v1 to v2 資料遷移腳本 | `scripts/migrate_v1_to_v2.py` | P2 | ✅ 完成 (含 --check / --migrate / --force) |
| 備份恢復測試 | `scripts/test_backup_recovery.py` | P2 | ✅ 完成 (自動化驗證) |
| Task Scheduler 設定 | `docs/deployment_guide.md` | P2 | ✅ 完成 (含排程說明) |
| 生產環境部署與驗證 | `docs/deployment_guide.md` | P1 | ✅ 完成 (含完整部署指南) |
| 用戶培訓與文件 | `docs/deployment_guide.md` | P2 | ✅ 完成 |
| 🆕 DB 路徑統一化 | `config.py`, `backend/config.py` 等 | P0 | ✅ 完成 (root ↔ backend 統一至 v2 路徑) |
| 🆕 13 模型選擇器增強 | `backend/config.py`, Chat UI | P1 | ✅ 完成 (含分類、成本標籤、下拉選單) |
| 🆕 BYOK Header 修復 | `frontend/client/api_client.py` | P1 | ✅ 完成 (15+ 方法補上 _build_headers) |
| 🆕 Legacy 程式碼清除 | chat_app.py, admin_app.py 等 | P1 | ✅ 完成 (刪除 5 個舊檔案) |
| 🆕 Models API 端點 | `backend/app/api/v1/models.py` | P1 | ✅ 完成 (/api/v1/models/list) |
| 🆕 Stats.py 路徑修復 | `frontend/pages/3_📊_Stats.py` | P1 | ✅ 完成 |
| 🆕 Scripts 路徑修復 | `scripts/cleanup.py`, `backup_db.bat` | P1 | ✅ 完成 |
| 🆕 .gitignore 建立 | `.gitignore` | P2 | ✅ 完成 |
| **Phase 4 小計** | | | **43h (~6 工作天)** |

#### ⏳ Phase 5: 長期優化 (Future)
**目標**: 持續監控、搜尋優化、完整 E2E 測試

| 任務 | Target | 優先級 | 狀態 |
|---|---|---|---|
| Prometheus Metrics | `middleware/monitoring.py` | P2 | ✅ 完成 (輕量收集器 + /metrics 端點) |
| 搜尋最佳化 (向量索引) | `core/search/search_cache.py` | P2 | ✅ 完成 (Embedding LRU + 結果 TTL 快取) |
| E2E 測試 (Playwright) | `tests/e2e/` | P2 | ✅ 完成 (Chat/Admin/API 3 套測試) |
| API 文件完善 | `main.py` docstrings | P2 | ✅ 完成 (13 端點 Google-style docstrings) |
| 壓力測試 100 並發 | `tests/load_test.py` | P1 | ✅ 完成 (Locust + M4 驗收標準) |
| 並行運行觀察期 | `docs/observation_checklist.md` | P2 | ✅ 完成 (2 週觀察清單) |

### 19.3 關鍵里程碑 (Milestones)
| 里程碑 | 時間點 | 驗收標準 |
|---|---|---|
| **M1: Alpha 版本** | Week 2 結束 | 基本對話功能可用，Chat UI 可連接 Backend |
| **M2: Beta 版本** | Week 4 結束 | 所有 P0/P1 功能完成，通過整合測試 |
| **M3: RC 版本** | Week 6 結束 | 通過壓力測試 (50 並發)，監控系統上線 |
| **M4: 正式發布** | Week 7-8 | 100 並發測試通過，內部試運行 2 週無重大問題 |

### 19.4 風險預警與應對
| 風險 | 嚴重性 | 應對策略 |
|---|---|---|
| SQLite Lock 問題 | 🔴 高 | 提前進行 100 並發測試；備案: 切換至 PostgreSQL |
| LLM API 配額不足 | 🟠 中 | 通知用戶準備備用 API Key，限制單用戶高頻呼叫 |
| 前端無法完全移除 DB | 🟠 中 | 增加 Backend API 覆蓋度，確保所有功能可透過 API 實現 |
| 永久保留資料儲存空間不足 | 🟠 中 | 定期監控 DB 大小，必要時匯出舊資料至外部儲存 |
| 測試時間不足 | 🟡 低 | 優先保證 P0/P1 測試覆蓋率，P2 功能可延後 |

---

## 20. 已確認決策摘要 (Confirmed Decisions)

以下為專案關鍵決策，已經確認並納入實施計畫：

### 20.1 技術決策
| 項目 | 決策 | 理由 |
|---|---|---|
| **部署環境** | Windows 原生（無容器） | 簡化部署，降低維護複雜度 |
| **資料保留** | Chat History 永久保留 | 用戶需求，需擴充儲存空間規劃 |
| **Rate Limiting** | 30 req/min, 500 req/hour | 平衡防護與可用性 |
| **Session 策略** | 24 小時自動過期 | 標準安全實踐 |
| **備份頻率** | Chat: 6h, Knowledge: 12h | 平衡資料安全與效能 |
| **降級策略** | 不實作 API 自動切換 | 簡化架構，用戶自行管理 Key |
| **多語言** | 僅支援繁體中文 | 聚焦目標用戶 |
| **測試覆蓋** | Unit ≥ 80%, Integration ≥ 70% | 確保高品質交付 |

### 20.2 簽核欄
- **計畫提出**: AI Agent (GitHub Copilot)
- **技術審核**: ________________ (日期: ______)
- **業務審核**: ________________ (日期: ______)
- **最終核准**: ________________ (日期: ______)

---

## 21. 附錄 (Appendix)

### 21.1 技術棧總覽
| 類別 | 技術 | 版本要求 | 用途 |
|---|---|---|---|
| **後端框架** | FastAPI | ≥ 0.109.0 | REST API Server |
| **前端框架** | Streamlit | ≥ 1.31.0 | Chat & Admin UI |
| **資料庫** | SQLite | ≥ 3.35.0 | 知識庫、對話記錄 (需支援 WAL) |
| **非同步框架** | asyncio | 內建 | 高併發處理 |
| **LLM SDK** | openai, google-generativeai | Latest | AI 模型呼叫 |
| **Token 計算** | tiktoken | Latest | 精確 Token 統計 |
| **限流** | slowapi | ≥ 0.1.9 | Rate Limiting |
| **重試** | tenacity | ≥ 8.2.0 | API 重試機制 |
| **監控** | prometheus-client | ≥ 0.19.0 | Metrics 收集 |
| **測試** | pytest, locust, playwright | Latest | 測試框架 |
| **部署** | uvicorn | ≥ 0.27.0 | ASGI Server |
| **服務管理** | NSSM | Latest | Windows 服務化 (可選) |

### 21.2 預估資源需求 (50~100 人)
| 資源 | 最低配置 | 推薦配置 |
|---|---|---|
| **CPU** | 4 Cores | 8 Cores |
| **RAM** | 8 GB | 16 GB |
| **儲存空間** | 100 GB (永久保留) | 500 GB+ (含備份與擴展) |
| **網路頻寬** | 100 Mbps | 1 Gbps |
| **OS** | Windows 10 Pro 或 Windows Server 2019+ | Windows Server 2022 |

### 21.3 參考資料
- [FastAPI 官方文件](https://fastapi.tiangolo.com/)
- [SQLite WAL Mode](https://www.sqlite.org/wal.html)
- [OpenAI API 文件](https://platform.openai.com/docs/api-reference)
- [Streamlit 部署指南](https://docs.streamlit.io/streamlit-community-cloud/get-started/deploy-an-app)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)

---

## 22. 版本記錄 (Version History)
| 版本 | 日期 | 變更摘要 |
|---|---|---|
| **v2.3.0** | 2025-06-24 | ✅ Phase 4 深度整合完成：<br>- DB 路徑統一化 (root ↔ backend 指向同一 v2 DB)<br>- 13 模型選擇器 (含 OpenAI + Gemini + 圖片模型)<br>- BYOK Header 修復 (15+ API 方法)<br>- Legacy 程式碼清除 (刪除 5 個舊檔案)<br>- 遷移腳本 + 備份恢復測試 + 部署指南<br>- .gitignore + __pycache__ 清理 |
| **v2.2.0** | 2026-02-13 | 🔄 根據用戶需求調整：<br>- 移除 Docker/Nginx/Systemd 配置，專注 Windows 原生部署<br>- 更新為永久保留 Chat History<br>- 移除 OpenAI↔Gemini 降級策略<br>- 移除多語言支援計畫<br>- 更新總工時至 260 小時 (33 工作天) |
| **v2.1.0** | 2026-02-13 | 🆕 新增完整測試策略、監控告警、備份恢復機制<br>🆕 新增錯誤處理、Rate Limiting、Session 管理<br>🆕 新增 GDPR 合規、圖片處理增強、Token 精確計算<br>🆕 新增四階段實施時程與優先級規劃<br>🆕 新增部署方案 (Docker/Nginx/Health Check)<br>🆕 新增風險預警與審核簽核流程 |
| **v2.0.0** | [原始日期] | 初版：核心架構定義、前後端分離、BYOK 身份驗證 |

---

**📌 最後更新**: 2025-06-24 (v2.3.0)  
**📧 問題回報**: 請在專案 Issue Tracker 提交  
**⏱️ 預計總工時**: 約 **260 小時** (約 **33 個工作天**，1 人滿載)  
**👥 建議團隊配置**: 2-3 名全職開發者，可於 **3-4 週**內完成 Phase 1-3  
**🖥️ 部署環境**: Windows 原生（已移除 Docker/Nginx/Linux 相關配置）  
**💾 資料策略**: Chat History 永久保留，需規劃充足儲存空間
