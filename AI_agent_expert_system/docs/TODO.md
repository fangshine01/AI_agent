# AI Expert System - 待辦事項清單

> **最後更新**: 2026-02-12  
> **當前狀態**: 核心功能已完成 (~95%)，剩餘項目為測試驗證與可選優化

---

## 🔥 必須完成項目 (P0)

### 1. 環境初始化
- [ ] **安裝後端依賴**: `pip install -r backend/requirements.txt`
- [ ] **安裝前端依賴**: `pip install -r frontend/requirements.txt`
- [ ] **初始化資料庫**: `python scripts/init_db.py`
- [ ] **配置環境變數**: 複製 `.env.example` → `.env`，填入 API Keys

### 2. 整合測試 (Phase 8)
- [ ] **端對端測試流程 1: 自動化入庫**
  - [ ] 上傳包含圖表的 PPT 到前端
  - [ ] 觀察後端日誌確認 Watcher 觸發
  - [ ] 驗證檔案移到 `archived_files`
  - [ ] 驗證 `generated_md` 有生成檔案
  - [ ] 在前端搜尋相關內容
  - [ ] 確認可下載原始檔案

- [ ] **端對端測試流程 2: 圖文處理**
  - [ ] 查看生成的 Markdown 內容
  - [ ] 驗證表格/流程圖正確轉換
  - [ ] 在前端測試 Mermaid 渲染

- [ ] **端對端測試流程 3: 錯誤處理**
  - [ ] 上傳損壞檔案，確認移至 `failed_files`
  - [ ] 測試 API 錯誤處理
  - [ ] 測試網路中斷情況

- [ ] **效能測試**
  - [ ] 批次上傳 50 個檔案，測試 Watcher 處理速度
  - [ ] 監控 Token 消耗 (OpenAI + Gemini)
  - [ ] 壓力測試: 並發 10 個查詢請求

---

## ⭐ 重要但非阻塞項目 (P1)

### 3. 網路安全設定 ✅
- [x] **防火牆規則配置**
  - [x] 建立 `setup_firewall.bat` 一鍵設定腳本
  - [x] 限制只允許局域網 IP 存取
  - [x] 驗證外網無法連接

- [x] **API Key 驗證系統** (可選，但強烈建議生產環境啟用)
  - [x] 建立 API Key 中介層 (`backend/app/middleware/api_auth.py`)
  - [x] 整合到 FastAPI 主程式
  - [x] 更新前端 API Client 支援 X-API-Key header
  - [x] 建立環境變數範本 (`.env.example`)
  - [x] 撰寫啟用指南 (`SECURITY_SETUP_GUIDE.md`)
  - [ ] **使用者執行**: 產生 API Key 並設定到 `.env`
  - [ ] **使用者執行**: 測試驗證機制是否生效

### 4. 自動化測試腳本
- [ ] 執行後端測試: `pytest backend/tests/ -v`
  - [ ] `test_api.py` - API 端點測試
  - [ ] `test_watcher.py` - 檔案監控測試
  - [ ] `test_image_processor.py` - Gemini 處理器測試
  - [ ] `test_ingestion.py` - 入庫流程測試

---

## 💡 可選優化項目 (P2)

### 5. 程式碼品質
- [ ] 執行 Linter: `pylint backend/ frontend/`
- [ ] 格式化程式碼: `black backend/ frontend/`
- [ ] 準備 Gemini 測試圖片資料集

### 6. 容器化部署 (可選)
- [ ] 建立 `Dockerfile` (後端)
- [ ] 建立 `Dockerfile` (前端)
- [ ] 建立 `docker-compose.yml` (一鍵部署)

### 7. 共享模組 (可選)
- [ ] 建立 `shared/constants.py` (共享常數)
- [ ] 建立 `shared/__init__.py`

---

## ✅ 已完成項目總覽

### Phase 1: 環境準備 ✅
- ✅ 建立後端目錄結構
- ✅ 建立前端目錄結構
- ✅ 建立資料目錄
- ✅ 更新依賴套件清單
- ✅ 建立環境配置範例
- ✅ 建立資料庫初始化腳本

### Phase 2: 檔案監控服務 ✅
- ✅ 實作 `backend/app/services/file_watcher.py` (247 行)
- ✅ 編寫測試 `backend/tests/test_watcher.py`

### Phase 3: Gemini 圖片處理 ✅
- ✅ 實作 `backend/app/core/image_processor.py` (122 行)
- ✅ 編寫測試 `backend/tests/test_image_processor.py`

### Phase 4: Ingestion 升級 ⏳
- ✅ 透過 `dependencies.py` 橋接現有 `core/ingestion_v3.py`
- ✅ 儲存生成的 Markdown 到 `generated_md/`
- ⏳ 待完成: Gemini 整合到 ingestion 流程

### Phase 5: FastAPI API 實作 ✅
- ✅ 實作 `backend/app/main.py` (生命週期管理、路由註冊)
- ✅ 實作 5 個 API 路由模組 (15 個端點)
- ✅ 實作 Pydantic Schemas
- ✅ 實作中介層 (CORS, Token Tracker)

### Phase 6: 前端 API 客戶端 ✅
- ✅ 建立 `frontend/client/api_client.py` (290+ 行, 16 方法)

### Phase 7: 前端 UI 重構與優化 ✅
- ✅ 建立 `frontend/Home.py`✅
- ✅ 透過 `dependencies.py` 橋接現有 `core/ingestion_v3.py`
- ✅ 新增參數: `enable_gemini_vision`, `parent_doc_id`
- ✅ 實作 `_process_image_with_gemini()` 函數 (完整圖片處理流程)
- ✅ 整合 Gemini Vision API 到 ingestion 流程
- ✅ 資料庫入庫邏輯 (記錄 parent_doc_id, source_type)
- ✅ 更新 Token 追蹤邏輯 (包含 Gemini 用量)
- ✅ 儲存生成的 M (test_api.py, test_watcher.py, test_image_processor.py, test_ingestion.py)
- ⏳ 待手動執行測試流程

### Phase 9: 部署腳本 ✅
- ✅ 建立 `start_v2.bat` (整合啟動腳本，支援 Network URL)
- ✅ 建立 `scripts/start_backend.py`
- ✅ 建立 `scripts/start_frontend.py`
- ✅ 修正 PYTHONPATH 環境變數設定

### Phase 10: 文檔 ✅
- ✅ 更新 `README.md` (v2.0 架構說明)
- ✅ 建立 `backend/README.md`
- ✅ 建立 `frontend/README.md`
- ✅ 建立 `ARCHITECTURE_OVERVIEW.md` (完整架構文檔)
- ✅ 更新 `README.md` (v2.0 架構說明)
- ✅ 建立 `backend/README.md`
- ✅ 建立 `frontend/README.md`
- ✅ 建立 `docs/ARCHITECTURE.md`

---

## 📊 完成度統計

| 階段 | 狀態 | 完成度 |
|------|------|--------|
| Phase 1: 環境準備 | ✅ | 100% |
| Phase 2: 檔案監控 | ✅ | 100% |
| Phase 3: Gemini 處理 | ✅ |✅ | 100% |
| Phase 5: FastAPI API | ✅ | 100% |
| Phase 6: API Client | ✅ | 100% |
| Phase 7: 前端 UI | ✅ | 100% |
| Phase 8: 整合測試 | ⏳ | 0% (待執行) |
| Phase 9: 部署腳本 | ✅ | 100% |
| Phase 10: 文檔 | ✅ | 100% |
| **總體** | **⏳** | **~90% |
| **總體** | **⏳** | **~85%** |

---

## 🚀 快速啟動指南

### 首次使用
```bash
# 1. 安裝依賴
pip install -r backend/requirements.txt
pip install -r frontend/requirements.txt

# 2. 初始化資料庫
python scripts/init_db.py

# 3. 配置環境變數
copy .env.example .env
# 編輯 .env 填入 API Keys

# 4. 啟動系統 (Windows)
start_v2.bat
```

### 訪問地址
- **前端介面**: http://localhost:8501 (僅限本機)
- **後端 API**: http://localhost:8000
- **API 文件**: http://localhost:8000/docs

---

## 📝 技術備註

### core/ 模組位置說明
- **實際位置**: 保留在專案根目錄
- **引用方式**: 透過 `backend/app/dependencies.py` 中的 `sys.path` 注入
- **原因**: 維持向後相容，降低重構風險

### 已修復的 Bug
- ✅ `frontend/client/api_client.py`: `_request()` 通用方法
- ✅ `frontend/client/api_client.py`: `update_config()` 參數修正
- ✅ `backend/app/api/v1/admin.py`: `POST /batch/{action}` 端點
- ✅ `start_v2.bat`: Network URL 支援 (0.0.0.0)，禁用 External URL
- ✅ `start_v2.bat`: **自動偵測並顯示局域網 IP** (例: http://192.168.5.3:8501)
- ✅ `backend/app/dependencies.py`: 使用 pathlib.Path 解析路徑
- ✅ `core/ingestion_v3.py`: Gemini Vision 完整整合

### 新增功能與檔案
- ✅ **setup_firewall.bat**: 一鍵設定防火牆，僅允許局域網存取
- ✅ **.streamlit/config.toml**: Streamlit 配置檔（監聽與主題設定）
- ✅ **QUICKSTART.md**: 網路安全配置章節（三層防護說明）
- ✅ **backend/app/middleware/api_auth.py**: API Key 驗證中介層
- ✅ **SECURITY_SETUP_GUIDE.md**: 完整的安全設定教學文件（逐步指引）
- ✅ **frontend/client/api_client.py**: 支援 X-API-Key header 自動攜帶

---

## 🔒 安全性設定狀態

### 已實作功能
| 功能 | 狀態 | 說明 |
|-----|------|-----|
| 防火牆腳本 | ✅ 完成 | `setup_firewall.bat` - 一鍵限制局域網存取 |
| API Key 中介層 | ✅ 完成 | 完整驗證機制，支援白名單和日誌記錄 |
| 前端 API Client | ✅ 完成 | 自動從環境變數讀取並攜帶 API Key |
| 環境變數範本 | ✅ 完成 | `.env.example` 加入 `ENABLE_API_AUTH` 和 `SYSTEM_API_KEY` |
| 啟用開關設計 | ✅ 完成 | 可透過 `ENABLE_API_AUTH=true/false` 切換 |
| 文件指引 | ✅ 完成 | 三份文件：SECURITY.md / QUICKSTART.md / SECURITY_SETUP_GUIDE.md |

### 使用者待辦事項
1. [ ] 產生自己的 API Key: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
2. [ ] 編輯 `.env` 檔案，加入 `ENABLE_API_AUTH=true` 和 `SYSTEM_API_KEY`
3. [ ] 重啟系統: `start_v2.bat`
4. [ ] 驗證是否生效（參考 [SECURITY_SETUP_GUIDE.md](SECURITY_SETUP_GUIDE.md)）

**預設狀態**: API Key 驗證 **關閉**（開發友善），使用者可選擇啟用（生產環境建議開啟）
- ✅ **ARCHITECTURE_OVERVIEW.md**: 完整架構文檔（600+ 行）

---

## 📚 相關文件

- `QUICKSTART.md` - 快速啟動指南（含網路安全配置）
- `ARCHITECTURE_OVERVIEW.md` - **完整架構文檔** (新增)
- `backend/README.md` - 後端 API 文檔
- `frontend/README.md` - 前端組件說明
- `audit_report.md` - 專案稽核報告
- `optimization_summary.md` - 搜尋系統優化建議
- `generalization_proposal.md` - 通用化方案
- `audit_report.md` - 專案稽核報告
