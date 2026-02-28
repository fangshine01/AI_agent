# 系統網路架構與認證機制說明 (Network & Authentication Guide)

本文檔說明本系統在 **不使用 Docker 或容器技術** 的情況下，如何實現前後端分離、網路通訊，以及 API 的安全認證機制。

## 1. 非容器化 (Non-Docker) 運作原理

### 多行程架構 (Multi-Process Architecture)
本系統由三個獨立的 Python 行程 (Process) 組成，它們直接在作業系統 (Windows/Linux) 上執行，各自監聽不同的 **連接埠 (Port)**。

```mermaid
graph TD
    User[使用者瀏覽器] -->|Port 8501| ChatUI[Chat Interface (Streamlit)]
    Admin[管理員瀏覽器] -->|Port 8502| AdminUI[Admin Dashboard (Streamlit)]
    
    ChatUI -->|HTTP Request (Port 8000)| Backend[Backend API (FastAPI)]
    AdminUI -->|HTTP Request (Port 8000)| Backend
    
    Backend -->|Read/Write| DB[(SQLite Database)]
```

### 為什麼不需要 Docker？
Docker 的作用是環境隔離。在內部網路或單機部署時，我們可以直接利用 OS 的網路堆疊 (TCP/IP Stack)。
*   **Backend (FastAPI)** 啟動一個 HTTP Server (Uvicorn)，綁定在 `0.0.0.0:8000`，等待請求。
*   **Frontend (Streamlit)** 啟動 Web Server，綁定在 `0.0.0.0:8501`，服務使用者。
*   **通訊方式**：前端 Python 程式碼使用 `requests` 函式庫，向 `http://localhost:8000` 或 `http://<Backend-IP>:8000` 發送標準 HTTP 請求。

---

## 2. 網路連結設定與技巧

### 本機部署 (Localhost)
若前後端都在同一台電腦上執行：
*   **API URL**: 設定為 `http://localhost:8000` 或 `http://127.0.0.1:8000`。
*   **延遲**: 極低 (<1ms)，適合測試與開發。

### 區網部署 (LAN / Cross-Machine)
若後端在 Server A (IP: 192.168.1.100)，前端在 Server B 或使用者電腦：
1.  **Backend 啟動參數**: 必須設定 `--host 0.0.0.0`，允許外部連線。
    ```bash
    uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
    ```
2.  **Frontend 設定**: 前端程式需指向後端 IP。
    ```python
    # frontend/config.py 或 環境變數
    API_BASE_URL = "http://192.168.1.100:8000"
    ```
3.  **防火牆 (Firewall)**: Server A 的 Windows 防火牆必須設定「**允許 Port 8000 通過**」。

---

## 3. FastAPI 認證機制 (Authentication)

本系統採用 **Header-based API Key Authentication**，這是一種輕量且標準的 RESTful 認證方式。

### 認證流程 (Authentication Flow)

1.  **使用者輸入 Key**: 
    使用者在 Streamlit 介面輸入 GPT API Key (例如 `sk-...`).

2.  **前端請求封裝**: 
    前端在發送每一個 HTTP 請求給後端時，會自動在 Header 加入 `X-API-Key`。
    ```python
    # 前端 Python 範例
    headers = {
        "X-API-Key": user_input_key,
        "Content-Type": "application/json"
    }
    response = requests.post(f"{BASE_URL}/api/v1/chat/query", json=payload, headers=headers)
    ```

3.  **後端中間件攔截 (Backend Middleware)**:
    FastAPI 後端設有安全閘門 (Middleware/Dependency)，在處理任何邏輯前先檢查：
    *   **檢查 Header**: 是否包含 `X-API-Key`？
    *   **驗證有效性**: (可選) 檢查 Key 格式是否正確。
    *   **身份識別 (Identity)**: 
        *   系統將 Key 進行雜湊 (Hash) 處理：`user_id = SHA256(api_key)`。
        *   以此 `user_id` 作為該次請求的身份證，用於讀取該用戶的歷史對話。

### 安全優勢
*   **Stateless (無狀態)**：伺服器不需要 Session Server，擴充容易。
*   **BYOK (Bring Your Own Key)**：直接利用 GPT Key 兼作身份驗證與計費憑證，簡化帳號管理系統。
*   **HTTPS 建議**: 在正式環境中，建議透過 SSL/TLS (HTTPS) 加密傳輸，避免 API Key 在網路上被側錄。但在內網 (Intranet) 環境中，HTTP 通常是可接受的。

---

## 4. 常見連接問題排除 (Troubleshooting)

| 問題現象 | 可能原因 | 排解方法 |
|---|---|---|
| **Connection Refused** | 後端沒啟動 或 Port 錯誤 | 確認 `run_backend.bat` 視窗是否開啟且無錯誤。確認 URL Port 為 8000。 |
| **Connection Timed Out** | 防火牆擋住 | 檢查後端電腦的防火牆設定，允許 TCP Port 8000 入站規則。 |
| **401 Unauthorized** | 未提供 API Key | 前端確認是否已輸入 Key，且 Header 名稱為 `X-API-Key`。 |
| **422 Validation Error** | 請求格式錯誤 | 前後端資料定義 (Schema) 不一致，檢查 `api_client` 程式碼。 |
