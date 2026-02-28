# AI Expert System - 安全性評估與風險分析

> **日期**: 2026-02-12  
> **當前安全等級**: ⚠️ 中風險（僅適合內部網路使用）

---

## 🔒 安全性現況分析

### ✅ 安全的部分（不用擔心）

#### 1. 程式碼安全
- ✅ **前端程式碼**: Streamlit 不會暴露 Python 原始碼，只提供 HTML/CSS/JavaScript
- ✅ **後端程式碼**: FastAPI 只提供 API 端點，不會暴露 Python 原始碼
- ✅ **系統檔案**: 作業系統層級的檔案無法透過瀏覽器存取

**結論**: 別人無法透過 IP 複製你的程式碼 ✅

---

### ⚠️ 有風險的部分（需要注意）

#### 1. 文件資料可能被存取 ❌

**風險**: 任何知道你 IP 的人都可以：

| 端點 | 風險 | 可存取的資料 |
|------|------|-------------|
| `/api/v1/files/list` | 🔴 高 | 列出所有已上傳的檔案名稱 |
| `/api/v1/files/download/{filename}` | 🔴 高 | 下載任何已上傳的檔案 |
| `/files/archived/*` | 🔴 高 | 直接存取已處理的檔案 |
| `/files/generated/*` | 🔴 高 | 直接存取 Gemini 生成的 Markdown |
| `/api/v1/admin/documents` | 🟡 中 | 查看文件列表與元數據 |
| `/api/v1/admin/stats` | 🟡 中 | 查看系統統計資訊 |
| `/api/v1/search/semantic` | 🟡 中 | 搜尋文件內容 |
| `/docs` | 🟡 中 | 查看完整 API 文檔 |

**實際測試範例**:
```bash
# 任何人只要知道你的 IP，就可以：

# 1. 列出所有檔案
curl http://192.168.5.3:8000/api/v1/files/list

# 2. 下載機密文件
curl http://192.168.5.3:8000/api/v1/files/download/機密報告.pptx -o downloaded.pptx

# 3. 查看 API 文檔
http://192.168.5.3:8000/docs

# 4. 搜尋敏感資訊
curl -X POST http://192.168.5.3:8000/api/v1/search/semantic \
  -H "Content-Type: application/json" \
  -d '{"query": "密碼", "top_k": 10}'
```

#### 2. API 文檔完全公開 ⚠️

`/docs` 端點會顯示：
- 所有 API 端點清單
- 每個端點的參數格式
- 如何調用的範例

這讓攻擊者很容易知道如何存取你的資料。

#### 3. 無身分驗證機制 ⚠️

當前系統**沒有任何密碼或 API Key 驗證**：
- 任何人都可以調用 API
- 任何人都可以上傳檔案
- 任何人都可以刪除文件
- 任何人都可以查看所有資料

---

## 🛡️ 立即防護措施（三層保護）

### 第 1 層：網路隔離（已完成）✅

**當前狀態**: 
- ✅ 防火牆規則限制僅局域網存取
- ✅ 路由器未開放 Port Forwarding

**保護效果**: 
- ✅ 外網無法連接
- ⚠️ 局域網內任何人都可以存取

**風險評估**:
- 如果你的局域網只有信任的人 → **安全**
- 如果你的局域網有訪客或不信任的裝置 → **不安全**

---

### 第 2 層：禁用 API 文檔（推薦）

**目的**: 讓攻擊者無法輕易知道有哪些 API 端點

**修改方式**: 編輯 `backend/app/main.py`

```python
# 生產環境：禁用 API 文檔
app = FastAPI(
    title="AI Expert System API",
    version="2.0.0",
    description="...",
    docs_url=None,      # 禁用 /docs
    redoc_url=None,     # 禁用 /redoc
    openapi_url=None,   # 禁用 /openapi.json
    lifespan=lifespan
)

# 開發環境：保留 API 文檔
# app = FastAPI(
#     title="AI Expert System API",
#     version="2.0.0",
#     description="...",
#     lifespan=lifespan
# )
```

**優點**: 
- ✅ 快速簡單
- ✅ 不影響功能

**缺點**: 
- ⚠️ 開發除錯時不方便
- ⚠️ 只是「隱藏」，不是真正的保護

---

### 第 3 層：添加 API Key 驗證（強烈建議）

**目的**: 只有提供正確 API Key 的人才能存取

#### 方案 A: 簡易 API Key（推薦新手）

1. **設定 API Key** (在 `.env`)
   ```env
   # 系統存取密鑰（自己設定一個隨機字串）
   SYSTEM_API_KEY=your-secret-key-12345
   ```

2. **新增驗證中介層** (`backend/app/middleware/api_auth.py`)
   ```python
   from fastapi import Request, HTTPException
   from starlette.middleware.base import BaseHTTPMiddleware
   import os
   
   SYSTEM_API_KEY = os.getenv("SYSTEM_API_KEY", "")
   
   # 白名單：不需要驗證的端點
   PUBLIC_ENDPOINTS = [
       "/health",
       "/",
   ]
   
   class APIKeyMiddleware(BaseHTTPMiddleware):
       async def dispatch(self, request: Request, call_next):
           # 檢查是否為白名單端點
           if request.url.path in PUBLIC_ENDPOINTS:
               return await call_next(request)
           
           # 檢查 API Key
           api_key = request.headers.get("X-API-Key")
           if api_key != SYSTEM_API_KEY:
               raise HTTPException(
                   status_code=401,
                   detail="無效的 API Key"
               )
           
           return await call_next(request)
   ```

3. **啟用中介層** (在 `main.py`)
   ```python
   from app.middleware.api_auth import APIKeyMiddleware
   
   # 添加 API Key 驗證
   if os.getenv("ENABLE_API_AUTH", "false").lower() == "true":
       app.add_middleware(APIKeyMiddleware)
   ```

4. **前端配置** (`frontend/config.py`)
   ```python
   import os
   
   API_BASE_URL = "http://localhost:8000"
   SYSTEM_API_KEY = os.getenv("SYSTEM_API_KEY", "")
   
   # 所有 API 請求都帶上 API Key
   DEFAULT_HEADERS = {
       "X-API-Key": SYSTEM_API_KEY
   }
   ```

**使用方式**:
```bash
# 每次調用 API 都需要帶上 X-API-Key header
curl http://192.168.5.3:8000/api/v1/files/list \
  -H "X-API-Key: your-secret-key-12345"
```

**優點**:
- ✅ 簡單易用
- ✅ 有效阻擋未授權存取
- ✅ 不影響正常使用者

**缺點**:
- ⚠️ API Key 如果洩漏，需要更改所有配置
- ⚠️ 無法區分不同使用者

---

#### 🎯 方案 A: 快速啟用內建 API Key 驗證（已實作）

**系統已經內建 API Key 驗證功能，只需 3 步驟即可啟用！**

**步驟 1: 產生安全的 API Key**
```bash
# 使用 Python 產生 32 字元的隨機密鑰
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 輸出範例：
# XyZ9_AbC123-dEfGhI456jKlMnOpQ789rStUvWxYz
```

**步驟 2: 設定環境變數** (編輯 `.env`)
```env
# 啟用 API Key 驗證
ENABLE_API_AUTH=true

# 填入剛產生的 API Key
SYSTEM_API_KEY=XyZ9_AbC123-dEfGhI456jKlMnOpQ789rStUvWxYz
```

**步驟 3: 重啟系統**
```bash
# Windows: 執行啟動腳本
start_v2.bat

# 啟動時會顯示安全狀態：
# [2024-05-20 10:30:00] INFO: ✅ API Key 驗證已啟用
```

**驗證是否生效**:
```bash
# 測試 1: 沒有 API Key → 應該被拒絕 (401 Unauthorized)
curl http://192.168.5.3:8000/api/v1/files/list

# 測試 2: 帶上正確的 API Key → 成功存取
curl http://192.168.5.3:8000/api/v1/files/list \
  -H "X-API-Key: XyZ9_AbC123-dEfGhI456jKlMnOpQ789rStUvWxYz"

# 測試 3: 前端應用會自動帶上 API Key (透過環境變數讀取)
# 瀏覽器存取 http://192.168.5.3:8501 應該正常運作
```

**內建保護功能**:
- ✅ 所有 API 端點都需要驗證
- ✅ 白名單機制 (Health Check / 首頁無需驗證)
- ✅ 詳細的未授權日誌記錄
- ✅ 前端自動攜帶 API Key
- ✅ 可隨時開關 (不影響開發模式)

**日誌監控**:
```log
# 系統啟動時
[INFO] ✅ API Key 驗證已啟用
[INFO] 🔒 受保護端點: /api/v1/*, /files/*, /docs, /redoc

# 有人嘗試未授權存取
[WARNING] 🚫 未授權存取: 
  - IP: 192.168.5.100
  - 端點: /api/v1/files/download/secret.pdf
  - 時間: 2024-05-20 15:30:00
  - 原因: Missing API Key
```

---

#### 方案 B: 使用者帳密系統（適合多人使用）

需要實作：
- JWT Token 驗證
- 使用者註冊/登入
- 權限管理（Admin/User）
- Session 管理

**優點**:
- ✅ 可以追蹤誰做了什麼
- ✅ 可以設定不同權限
- ✅ 更安全

**缺點**:
- ⚠️ 實作複雜
- ⚠️ 需要資料庫儲存使用者資訊
- ⚠️ 需要登入頁面

---

### 第 4 層：IP 白名單（額外防護）

**目的**: 只允許特定 IP 存取

**實作方式** (`backend/app/middleware/ip_whitelist.py`):
```python
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

ALLOWED_IPS = [
    "127.0.0.1",           # 本機
    "192.168.5.3",         # 你的電腦
    "192.168.5.10",        # 同事A
    "192.168.5.11",        # 同事B
]

class IPWhitelistMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        
        if client_ip not in ALLOWED_IPS:
            raise HTTPException(
                status_code=403,
                detail=f"IP {client_ip} 未被授權存取"
            )
        
        return await call_next(request)
```

---

## 📊 安全等級比較

| 防護措施 | 安全等級 | 實作難度 | 適用場景 |
|---------|---------|---------|---------|
| **僅防火牆** | ⚠️ 低 | ✅ 簡單 | 家庭網路（只有自己） |
| **防火牆 + 禁用 Docs** | ⚠️ 中低 | ✅ 簡單 | 小型辦公室（信任所有人） |
| **防火牆 + API Key** | ✅ 中高 | 🟡 中等 | 辦公室（有訪客或臨時人員） |
| **API Key + IP 白名單** | ✅ 高 | 🟡 中等 | 嚴格控制環境 |
| **使用者帳密系統** | ✅ 最高 | 🔴 複雜 | 多人團隊使用 |

---

## 🎯 建議做法（依情境）

### 情境 1: 家庭使用（只有自己）
```
✅ 當前的防火牆規則已足夠
→ 不需要額外防護
```

### 情境 2: 小型辦公室（信任所有網路使用者）
```
✅ 防火牆規則
✅ 禁用 API 文檔
→ 降低被攻擊的風險
```

### 情境 3: 辦公室有訪客 WiFi 或臨時人員
```
✅ 防火牆規則
✅ 禁用 API 文檔
✅ 啟用 API Key 驗證  ← 強烈建議
→ 確保只有授權人員可以存取
```

### 情境 4: 多人團隊使用
```
✅ 防火牆規則
✅ 使用者帳密系統
✅ 角色權限管理
→ 完整的存取控制
```

---

## ⚡ 快速實作：API Key 驗證

我可以幫你建立一個簡單的 API Key 驗證系統。需要以下步驟：

1. **建立驗證中介層**
2. **修改 main.py 啟用驗證**
3. **更新前端 API Client 帶上 API Key**
4. **設定 .env 的 SYSTEM_API_KEY**

是否需要我幫你實作？

---

## 🔐 資料保護最佳實踐

### 敏感資料處理
1. **機密文件**: 不要上傳到系統（或使用加密）
2. **API Keys**: 永遠存在 `.env`，不要提交到 Git
3. **資料庫備份**: 定期備份並加密
4. **日誌管理**: 不要記錄敏感資訊（密碼、API Key）

### 定期檢查
- [ ] 每月檢查誰連接過系統（查看日誌）
- [ ] 每月更新 API Key（如果有使用）
- [ ] 每季檢查防火牆規則是否正確
- [ ] 發現異常立即斷網並檢查

---

## 📚 延伸閱讀

- `QUICKSTART.md` - 網路安全配置章節
- `TROUBLESHOOTING.md` - 故障排除指南
- `ARCHITECTURE_OVERVIEW.md` - 系統架構文檔

---

## ✅ 總結

### 當前風險
| 問題 | 風險等級 | 影響 |
|------|---------|------|
| 程式碼被複製 | ✅ 無風險 | 無法透過 IP 取得程式碼 |
| 文件被下載 | 🔴 高風險 | 任何人都可以下載你的檔案 |
| 資料被搜尋 | 🟡 中風險 | 可以搜尋文件內容 |
| API 被濫用 | 🟡 中風險 | 可以上傳/刪除文件 |

### 建議行動
1. **立即**: 確認防火牆規則已啟用（阻擋外網）
2. **建議**: 禁用 API 文檔（隱藏端點）
3. **強烈建議**: 實作 API Key 驗證（如果有不信任的裝置在網路上）
4. **未來**: 實作完整的使用者系統（如果多人使用）

**最重要**: 如果你的局域網只有你自己或信任的人，當前的防火牆規則已經足夠安全！✅
