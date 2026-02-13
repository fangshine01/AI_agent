# SQLite 高併發與連線管理機制說明 (SQLite Concurrency & Connection Management)

本文檔詳細說明本系統如何使用 **SQLite WAL (Write-Ahead Logging)** 模式來支援 50~100 人同時在線的高併發場景，以及系統如何處理「同時匯入 (Write)」與「同時查詢 (Read)」的衝突。

## 1. 核心機制：WAL 模式 (Write-Ahead Logging)

### 什麼是 WAL？
傳統 SQLite (Rollback Journal) 在寫入時會鎖住整個資料庫，導致讀取被阻塞。
**WAL 模式** 改變了這一點：
- **寫入 (Write)**：資料不直接寫入主資料庫檔案 (`.db`)，而是追加到一個獨立的 WAL 檔案 (`.db-wal`)。
- **讀取 (Read)**：讀取操作會同時檢查主檔案與 WAL 檔案，取得最新資料。

### 優勢
1.  **讀寫分離 (Non-blocking Reads)**：**寫入者不會阻塞讀取者，讀取者也不會阻塞寫入者**。
2.  **併發性能**：允許多個讀取者 (Readers) 與一個寫入者 (Writer) 同時操作。

---

## 2. 場景模擬：同時匯入與查詢

當系統同時發生「管理員後台匯入大量文件」與「50 位使用者前台提問」時，系統運作如下：

| 角色 | 操作 | 系統行為 | 影響 |
|---|---|---|---|
| **Writer (管理員)** | 上傳/匯入文件 (Insert/Update) | 取得 **EXCLUSIVE Write Lock** (僅針對 WAL 檔)。<br>資料快速寫入 `.db-wal` 檔案。 | **不阻塞 Query**。<br>寫入完成瞬間，新的連線即可讀到新資料。 |
| **Reader (使用者)** | 問答/查詢 (Select) | 取得 **Snapshot Isolation**。<br>讀取當下的資料版本 (即從 `.db` + `.db-wal` 讀取)。 | **不等待 Write**。<br>即使管理員正在寫入，使用者仍可毫無延遲地讀取 (可能是寫入前的舊版資料，直到寫入 Commit)。 |

### 結論
**「匯入」與「查詢」可以並行執行，互不卡頓。**
使用者在查詢時，感覺不到資料庫被鎖定，體驗流暢。

---

## 3. 連線管理 (Connection Management)

為了支撐 50~100 人併發，FastAPI 後端採取以下策略管理 SQLite 連線：

### A. 請求級獨立連線 (Request-Scoped Connection)
*   **機制**：每個 HTTP Request 進來時，FastAPI 的 Dependency Injection (`get_db`) 會建立一個 **全新的 SQLite Connection**。
*   **目的**：確保不同使用者的操作完全隔離，互不干擾 transaction 狀態。
*   **生命週期**：Request 開始 -> `connect()` -> 執行 SQL -> Request 結束 -> `close()`。

### B. 單一寫入原則 (Single Writer Principle)
雖然 SQLite 支援多讀單寫，但為了避免 `database is locked` (當兩個連線同時嘗試寫入時)，我們建議：
*   **寫入操作 (Write)**：雖由不同 Request 觸發，SQLite 內部會自動排隊 (Queueing)。
*   **Busy Timeout**：設定 `timeout=60` 秒。若資料庫正忙 (正在 Checkpoint 或有其他寫入)，新的寫入請求會等待 60 秒而非直接報錯。

### C. 非同步非阻塞 (Async Non-blocking)
*   雖然 `sqlite3` 本身是同步 (Synchronous) 的，但 `uvicorn` Web Server 是非同步的。
*   我們會將長時間的寫入操作 (如大量匯入) 放入 **Background Tasks** 或 **Thread Pool**，確保它不會卡住 API 的主要 Event Loop，讓其他輕量級的讀取請求能繼續被處理。

---

## 4. 極限與擴充性 (Limitations & Scalability)

### SQLite 的極限
*   **適合**：讀多寫少 (Read-heavy) 或 讀寫混合但寫入非持續高頻。本系統場景 (知識庫查詢為主，偶爾匯入) 非常適合。
*   **不適合**：持續高頻寫入 (例如每秒 1000 次 Insert)。

### 未來擴充路徑
若未來使用者超過 500+ 或寫入量激增，架構已預留升級空間：
1.  **切換 PostgreSQL**：程式碼中 DB 操作已封裝於 `core/database`，只需更換 Driver 即可遷移至 PostgreSQL (支援多寫入併發)。
2.  **讀寫分離**：FastAPI 可設定多個 Read Replicas。

---

## 5. 總結

> **Q: 如果有人同時匯入與 Query，系統會如何處理？**
>
> **A: 兩者會同時進行。**
> *   **Query (使用者)** 會繼續讀取資料，完全不會感覺到卡頓。
> *   **Import (管理員)** 會在背景將資料寫入 WAL 檔，寫入完成後，新的 Query 就能立刻搜尋到新資料。
> *   系統透過 **WAL 模式** + **Busy Timeout** 機制，完美解決了傳統 SQLite 的鎖定問題。
