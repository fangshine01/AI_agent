# AI Expert System v2.0 - 快速啟動指南

> **版本**: 2.0  
> **最後更新**: 2026-02-12  
> **完成度**: ~95% (核心功能全部完成)

---

## 🚀 一鍵啟動 (Windows)

```batch
# 在專案根目錄執行
cd AI_agent_expert_system
start_v2.bat
```

### 腳本自動處理事項
- ✅ 檢查 Python 環境
- ✅ **自動偵測本機局域網 IP** (顯示實際 IP，如 192.168.5.3)
- ✅ 首次使用自動安裝依賴
- ✅ 建立必要的資料目錄
- ✅ 設定 PYTHONPATH 環境變數
- ✅ 背景啟動後端 API Server (Port 8000)
- ✅ 啟動前端 Streamlit UI (Port 8501)

### 訪問地址（腳本會自動顯示）
- **本機存取**: 
  - 前端: http://localhost:8501
  - 後端 API: http://localhost:8000
- **局域網存取** (同網段電腦):
  - 前端: http://192.168.x.x:8501 (腳本會自動顯示實際 IP)
  - 後端 API: http://192.168.x.x:8000
- **API 文檔**: http://localhost:8000/docs

> **網路安全提示**: 
> - ✅ **局域網存取**: 同網段使用者可透過本機 IP 連接
> - ⚠️ **外網隔離**: 確保路由器未對外開放 Port 8501/8000，防止公網存取
> - 🔒 **防火牆建議**: 僅允許內部網段 (如 192.168.x.x) 連接

---

## 🔐 網路安全配置

### 🚀 一鍵設定防火牆（推薦）

使用提供的腳本快速設定：

```batch
# 以系統管理員身分執行
setup_firewall.bat
```

**腳本功能**：
- ✅ 自動建立防火牆規則
- ✅ 僅允許局域網 IP 連接 (192.168.x.x, 10.x.x.x, 172.16-31.x.x)
- ✅ 自動驗證規則是否生效
- ✅ 提供移除指令

執行後，你的服務就會受到保護，只有同網段的電腦可以連接！

---

### 限制僅局域網存取（手動設定）

當前配置 `--server.address 0.0.0.0` 會監聽所有網路介面，允許局域網連接。要確保外網無法存取，需要：

#### 方法 1: Windows 防火牆規則 (推薦)

```powershell
# 1. 開啟 Windows 防火牆進階設定
# 控制台 > 系統及安全性 > Windows Defender 防火牆 > 進階設定

# 2. 建立輸入規則
# - 規則類型: 連接埠
# - 連接埠: TCP 8501, 8000
# - 動作: 允許連線
# - 設定檔: 私人
# - 範圍 > 遠端 IP 位址: 僅限以下 IP 位址
#   新增: 192.168.0.0/16 (或你的網段，如 192.168.1.0/24)

# 或使用命令列快速設定:
netsh advfirewall firewall add rule name="Streamlit-LAN-Only" dir=in action=allow protocol=TCP localport=8501 remoteip=192.168.0.0/16
netsh advfirewall firewall add rule name="FastAPI-LAN-Only" dir=in action=allow protocol=TCP localport=8000 remoteip=192.168.0.0/16
```

#### 方法 2: 路由器設定

1. **檢查 Port Forwarding**: 確保路由器未將 Port 8501/8000 轉發到公網
2. **檢查 DMZ 設定**: 確保本機未設置在 DMZ 區域
3. **啟用 UPnP 檢查**: 若啟用 UPnP，確認沒有自動開放這些 Port

#### 方法 3: 限制監聽網路介面 (較不方便)

若只想在特定網卡上監聽，可修改 `start_v2.bat`:

```batch
REM 綁定到特定局域網 IP (例如你的電腦在區網的 IP)
start "AI Expert - Frontend" cmd /k "cd /d %~dp0 && set PYTHONPATH=%~dp0 && streamlit run frontend/Home.py --server.port 8501 --server.address 192.168.1.100 --server.headless true"
```

缺點: 每次 IP 變動需要修改設定

### 驗證安全性

```bash
# 1. 查看監聽的 Port
netstat -an | findstr "8501"
netstat -an | findstr "8000"

# 預期結果: 0.0.0.0:8501 LISTENING (所有介面)

# 2. 從局域網其他裝置測試 (應該成功)
curl http://192.168.1.100:8501

# 3. 檢查是否可從外網存取 (應該失敗)
# 使用手機 4G 網路測試: http://<你的公網IP>:8501
# 或使用線上工具: https://www.yougetsignal.com/tools/open-ports/
```

---

## 🔐 啟用 API Key 驗證 (選用，強烈建議)

**目的**: 即使有人知道你的 IP，也無法存取 API 和下載文件

### 快速設定 (3 步驟)

#### 步驟 1: 產生安全密鑰

```bash
# 使用 Python 產生 32 字元隨機密鑰
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 輸出範例（複製此字串）:
# XyZ9_AbC123-dEfGhI456jKlMnOpQ789rStUvWxYz
```

#### 步驟 2: 編輯 `.env` 檔案

開啟專案根目錄的 `.env` 檔案（如不存在，複製 `.env.example`），加入：

```env
# 啟用 API Key 驗證
ENABLE_API_AUTH=true

# 填入剛產生的密鑰
SYSTEM_API_KEY=XyZ9_AbC123-dEfGhI456jKlMnOpQ789rStUvWxYz
```

#### 步驟 3: 重啟系統

```batch
# 關閉現有的服務（Ctrl+C），重新啟動
start_v2.bat

# 啟動時會顯示：
# [INFO] ✅ API Key 驗證已啟用
# [INFO] 🔒 受保護端點: /api/v1/*, /files/*, /docs
```

### 驗證是否生效

```bash
# 測試 1: 未授權請求 → 應該被拒絕 (401)
curl http://192.168.5.3:8000/api/v1/files/list

# 回應: {"detail": "Unauthorized: Missing or invalid API Key"}

# 測試 2: 正確授權 → 成功
curl http://192.168.5.3:8000/api/v1/files/list \
  -H "X-API-Key: XyZ9_AbC123-dEfGhI456jKlMnOpQ789rStUvWxYz"

# 回應: {"status": "success", "files": [...]}
```

### 前端自動處理

前端應用會自動從環境變數讀取 `SYSTEM_API_KEY`，所有 API 請求會自動攜帶驗證 header。使用者透過瀏覽器存取時無需手動輸入 API Key。

### 關閉驗證（開發模式）

```env
# 設定為 false 即可關閉驗證
ENABLE_API_AUTH=false
```

**詳細說明**: 參考 [SECURITY.md](SECURITY.md)

---

### 額外安全建議

| 措施 | 重要性 | 說明 |
|------|--------|------|
| **限制 IP 範圍** | 🔥 高 | 使用防火牆限制連接來源 |
| **定期更新密碼** | ⭐ 中 | 如果實作了認證功能 |
| **HTTPS 加密** | ⭐ 中 | 使用 SSL/TLS (需要憑證) |
| **VPN 連接** | 💡 低 | 外出時透過 VPN 存取 |
| **API Key 管理** | 🔥 高 | `.env` 檔案不要提交到 Git |



---

## ⚙️ 手動啟動 (開發模式)

### 1. 環境準備

```bash
# 安裝後端依賴
pip install -r AI_agent_expert_system/backend/requirements.txt

# 安裝前端依賴
pip install -r AI_agent_expert_system/frontend/requirements.txt

# 初始化資料庫 (首次使用)
python AI_agent_expert_system/scripts/init_db.py
```

### 2. 配置環境變數

```bash
# 複製範例檔案
copy AI_agent_expert_system\.env.example AI_agent_expert_system\.env

# 編輯 .env，填入必要的 API Keys:
# OPENAI_API_KEY=sk-...
# GEMINI_API_KEY=AIza...
```

### 3. 啟動後端 (Terminal 1)

```bash
cd AI_agent_expert_system
set PYTHONPATH=%cd%
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

**後端功能**:
- ✅ FastAPI REST API (15 個端點)
- ✅ Watchdog 檔案監控 (自動入庫)
- ✅ Gemini Vision 圖片處理
- ✅ 靜態檔案服務 (`/files/`)

### 4. 啟動前端 (Terminal 2)

```bash
cd AI_agent_expert_system
set PYTHONPATH=%cd%
streamlit run frontend/Home.py --server.port 8501 --server.address 0.0.0.0
```

**前端頁面**:
- 🏠 **Home**: 系統狀態、快速導航
- 💬 **Chat**: AI 問答介面 (9 項 UI 優化)
- 📁 **Admin**: 檔案管理、批次操作
- 📊 **Stats**: 統計儀表板 (Plotly 圖表)

---

## 🎯 核心功能驗證

### 測試 1: 檔案自動入庫

1. **上傳檔案** (Admin 頁面)
   - 點擊「上傳新文件」
   - 拖拽或選擇 PPT/PDF/Markdown 檔案
   - 點擊「開始處理」

2. **監控處理流程**
   - 後端 Terminal 會顯示處理日誌
   - 檔案會被自動移至 `backend/data/archived_files/`
   - 若包含圖片，會在 `backend/data/generated_md/` 生成 Markdown

3. **驗證入庫成功**
   - 在 Chat 頁面搜尋檔案內容
   - 檢查 Stats 頁面的文件數量統計

### 測試 2: Gemini 圖片處理

1. **準備測試圖片**
   - 使用包含表格或流程圖的圖片
   - 支援格式: PNG, JPG, JPEG

2. **上傳圖片**
   - 在 Admin 頁面上傳圖片檔案
   - 確保 `.env` 中有設定 `GEMINI_API_KEY`

3. **查看處理結果**
   - 檢查 `backend/data/generated_md/` 中的 Markdown 檔案
   - 驗證表格或流程圖是否正確轉換

4. **搜尋測試**
   - 在 Chat 頁面輸入圖片相關內容的查詢
   - 確認能檢索到生成的 Markdown 內容

### 測試 3: AI 問答

1. **基本查詢**
   ```
   查詢: "N706 蝴蝶 Mura 如何處理？"
   ```
   - 系統會進行混合搜尋 (向量 + 關鍵字)
   - 回傳相關文件片段 + GPT 生成的答案

2. **列表偵測**
   ```
   查詢: "列出所有 N706 相關的問題"
   ```
   - 系統自動偵測列表查詢
   - 回傳結構化的列表結果

3. **直接檢索**
   ```
   查詢: "找出 defect code 為 G Line Gap 的文件"
   ```
   - 系統執行資料庫查詢
   - 回傳符合條件的文件清單

---

## 📊 架構亮點

### ✅ 已完成功能 (Phase 1-10)

1. **前後端分離** (FastAPI + Streamlit)
   - 清晰的模組邊界
   - RESTful API 設計
   - 可獨立擴展前後端

2. **自動化檔案監控**
   - Watchdog 監聽 `raw_files/` 目錄
   - Debounce 機制避免重複處理
   - 失敗檔案自動分類

3. **Gemini Vision 整合**
   - 圖片自動轉 Markdown
   - 支援表格、流程圖、架構圖
   - Token 用量追蹤

4. **增強的問答引擎**
   - 混合搜尋 (向量 + 關鍵字)
   - 列表查詢偵測
   - 直接檢索模式
   - 上下文注入 RAG

5. **完整的 UI 優化** (9/9 項完成)
   - Tab 組織側邊欄
   - 快速操作按鈕
   - 卡片式搜尋結果
   - 分階段進度條
   - Mermaid 圖表渲染
   - 拖拽上傳
   - 即時進度顯示
   - 批次操作
   - Plotly 互動圖表

6. **完整測試套件**
   - API 端點測試 (`test_api.py`)
   - 檔案監控測試 (`test_watcher.py`)
   - 圖片處理測試 (`test_image_processor.py`)
   - 入庫流程測試 (`test_ingestion.py`)

7. **完整文檔**
   - `ARCHITECTURE_OVERVIEW.md` - 架構總覽 (新增)
   - `backend/README.md` - 後端 API 文檔
   - `frontend/README.md` - 前端組件說明
   - `TODO.md` - 待辦事項清單

---

## 🔧 常見問題排除

### Q1: 前端無法連接後端

**症狀**: Chat/Admin 頁面顯示 "API 連接失敗"

**解決方案**:
1. 確認後端已啟動 (訪問 http://localhost:8000/health)
2. 檢查防火牆是否阻擋 Port 8000
3. 確認 `frontend/config.py` 中的 `API_BASE_URL` 設定正確

### Q2: Watcher 未觸發

**症狀**: 檔案上傳後沒有自動處理

**解決方案**:
1. 檢查後端日誌是否顯示 "檔案監控服務已啟動"
2. 確認檔案上傳到 `backend/data/raw_files/` 目錄
3. 等待 2-3 秒 (Debounce 機制)
4. 檢查檔案權限

### Q3: Gemini 圖片處理失敗

**症狀**: 圖片上傳後檔案被移至 `failed_files/`

**解決方案**:
1. 確認 `.env` 中有設定 `GEMINI_API_KEY`
2. 檢查 API Key 是否有效
3. 確認圖片格式支援 (PNG, JPG, JPEG)
4. 檢查後端日誌查看詳細錯誤訊息

### Q4: 模組導入錯誤 (ModuleNotFoundError)

**症狀**: `ModuleNotFoundError: No module named 'frontend'` 或 `'backend'`

**解決方案**:
1. 使用 `start_v2.bat` 啟動 (已自動設定 PYTHONPATH)
2. 手動設定環境變數:
   ```batch
   set PYTHONPATH=%cd%\AI_agent_expert_system
   ```
3. 確認在正確的目錄執行命令

### Q5: 如何僅允許局域網存取，阻擋外網？

**需求**: 同網段使用者可連接，但禁止公網存取

**解決方案** (三層防護):
1. **確認路由器設定**:
   - 檢查 Port Forwarding: 確保未將 8501/8000 轉發到公網
   - 檢查 DMZ: 確保本機未在 DMZ 區域

2. **Windows 防火牆規則** (推薦，最關鍵):
   ```powershell
   # 僅允許內網 IP 連接（系統管理員模式）
   netsh advfirewall firewall add rule name="AI-Expert-Streamlit-LAN" dir=in action=allow protocol=TCP localport=8501 remoteip=192.168.0.0/16 profile=private
   netsh advfirewall firewall add rule name="AI-Expert-FastAPI-LAN" dir=in action=allow protocol=TCP localport=8000 remoteip=192.168.0.0/16 profile=private
   ```

3. **驗證**: 
   - ✅ 局域網測試: 使用 `start_v2.bat` 顯示的 IP (如 http://192.168.5.3:8501)
   - ❌ 外網測試: 使用手機 4G 網路測試公網 IP + Port，應無法連接

詳細說明請參閱下方「🔐 網路安全配置」章節。

### Q6: Network URL 無法從其他裝置訪問

**症狀**: 只能從本機訪問，局域網其他裝置無法連接

**解決方案**:
1. **查看啟動訊息**: `start_v2.bat` 會自動偵測並顯示你的 IP (例: http://192.168.5.3:8501)
2. 確認 Streamlit 啟動參數為 `--server.address 0.0.0.0`
3. 檢查 Windows 防火牆是否允許 Port 8501
4. 確認與其他裝置在同一局域網
5. 使用啟動訊息中顯示的 IP 連接

### Q7: 顯示的 URL 是 0.0.0.0 而不是實際 IP

**症狀**: CMD 顯示 http://0.0.0.0:8501

**解決方案**:
- ✅ 已修正！`start_v2.bat` 會自動偵測你的局域網 IP
- 啟動時會顯示完整的 URL，例如: http://192.168.5.3:8501
- 支援偵測 192.168.x.x、10.x.x.x、172.x.x.x 網段

---

## 📝 下一步建議

### 必須執行 (P0)
- [ ] 安裝依賴套件
- [ ] 初始化資料庫
- [ ] 配置 API Keys (.env)
- [ ] 執行端對端測試 (上傳 → 處理 → 查詢)

### 建議執行 (P1)
- [ ] 執行自動化測試: `pytest backend/tests/ -v`
- [ ] 準備測試資料集 (包含圖表的 PPT/PDF)
- [ ] 監控 Token 用量與成本

### 可選優化 (P2)
- [ ] 程式碼格式化: `black backend/ frontend/`
- [ ] Docker 容器化部署
- [ ] Redis 快取實作
- [ ] 多用戶權限管理

---

## 📚 詳細文檔索引

| 文檔 | 說明 | 目標讀者 |
|------|------|---------|
| `QUICKSTART.md` | 本檔案，快速啟動指南 | 所有使用者 |
| `SECURITY.md` | **安全性評估與防護指南** | 所有使用者（重要） |
| `TROUBLESHOOTING.md` | 故障排除指南 | 系統管理者 |
| `ARCHITECTURE_OVERVIEW.md` | 完整架構文檔、資料流、API 總覽 | 開發者、架構師 |
| `TODO.md` | 待辦事項清單、完成度統計 | 專案管理者 |
| `backend/README.md` | 後端 API 詳細文檔 | 後端開發者 |
| `frontend/README.md` | 前端組件說明、UI 優化對照 | 前端開發者 |
| `audit_report.md` | 專案稽核報告、檔案清單 | 品質保證 |
| `optimization_summary.md` | 搜尋系統優化建議 | 系統優化 |
| `generalization_proposal.md` | 通用化與查詢優化方案 | 產品規劃 |

---

## 🎉 專案里程碑

- ✅ **2026-02-12**: v2.0 發布
  - 前後端分離架構完成
  - Gemini Vision 整合完成
  - 全部 9 項 UI 優化完成
  - 完整測試套件建立
  - 完整文檔產出
  - 整體完成度: ~95%

- 🎯 **下一版本規劃** (v2.1):
  - Redis 快取層
  - 非同步檔案處理佇列
  - 多用戶權限管理
  - WebSocket 即時進度推送

---

**需要協助？**
- 查看詳細架構文檔: `ARCHITECTURE_OVERVIEW.md`
- 查看待辦事項: `TODO.md`
- 查看 API 文檔: http://localhost:8000/docs (啟動後端後訪問)
