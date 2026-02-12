# AI Expert System v2.0 - 架構設計文件

> 最後更新: 2026-02-12

---

## 1. 系統總覽

```
┌─────────────────────────────────────────────────────────┐
│                     使用者 (Browser)                      │
├──────────────────────┬──────────────────────────────────┤
│   Streamlit 前端      │   http://localhost:8501           │
│   (frontend/)        │   多頁面: Chat, Admin, Stats      │
├──────────────────────┼──────────────────────────────────┤
│                      │  httpx HTTP 通訊                   │
├──────────────────────┼──────────────────────────────────┤
│   FastAPI 後端        │   http://localhost:8000           │
│   (backend/)         │   RESTful API, Swagger docs       │
├──────────────────────┼──────────────────────────────────┤
│   Core 模組           │   core/ (根目錄)                  │
│   AI, DB, Search     │   ai_core, database, search, ...  │
├──────────────────────┼──────────────────────────────────┤
│   SQLite + sqlite-vec │   knowledge_v2.db                │
│   Token DB            │   tokenrecord_v2.db              │
├──────────────────────┼──────────────────────────────────┤
│   背景服務             │   Watchdog File Watcher          │
│                      │   Gemini Image Processor          │
└──────────────────────┴──────────────────────────────────┘
```

---

## 2. 目錄結構

```
AI_agent_expert_system/
├── backend/                    # FastAPI 後端
│   ├── app/
│   │   ├── main.py             # 入口 (lifespan, CORS, routes)
│   │   ├── dependencies.py     # 依賴注入 (橋接 core/ 模組)
│   │   ├── api/v1/             # API 路由
│   │   │   ├── chat.py         # POST /query (問答)
│   │   │   ├── ingestion.py    # POST /upload (上傳)
│   │   │   ├── files.py        # GET /list, /download
│   │   │   ├── admin.py        # 配置/統計/批次操作
│   │   │   └── search.py       # 語意/關鍵字搜尋
│   │   ├── core/
│   │   │   └── image_processor.py  # Gemini 圖片→Markdown
│   │   ├── services/
│   │   │   └── file_watcher.py     # Watchdog 自動入庫
│   │   ├── schemas/            # Pydantic v2 資料模型
│   │   ├── middleware/          # CORS, Token Tracker
│   │   └── utils/              # 檔案處理工具
│   ├── config.py               # 後端設定 (.env)
│   ├── data/                   # 資料目錄
│   │   ├── raw_files/          # 放入即自動處理
│   │   ├── archived_files/     # 處理完成歸檔
│   │   ├── generated_md/       # 圖片轉 Markdown 輸出
│   │   └── failed_files/       # 處理失敗
│   └── tests/                  # pytest 測試
│
├── frontend/                   # Streamlit 前端
│   ├── Home.py                 # 入口 (系統狀態+導航)
│   ├── pages/
│   │   ├── 1_💬_Chat.py       # 問答介面 (9 項 UI 優化)
│   │   ├── 2_📁_Admin.py      # 管理後台 (上傳/文件/設定/Token)
│   │   └── 3_📊_Stats.py      # 統計儀表板 (Plotly)
│   ├── client/api_client.py    # HTTP API 客戶端
│   ├── components/             # 可重用 UI 元件
│   └── utils/                  # Markdown/Mermaid 渲染
│
├── core/                       # 核心業務邏輯 (v1.x 保留)
│   ├── ai_core.py              # LLM 呼叫
│   ├── ingestion_v3.py         # 文件入庫
│   ├── database/               # SQLite + sqlite-vec
│   ├── search/                 # 通用搜尋引擎
│   ├── parsers/                # PPTX/PDF/MD 解析器
│   └── metadata_extractor.py   # AI 元資料提取
│
├── scripts/                    # 部署腳本
│   ├── init_db.py              # 資料庫初始化
│   ├── start_backend.bat       # 啟動後端
│   ├── start_frontend.bat      # 啟動前端
│   └── start_all.bat           # 一鍵全部啟動
│
└── .env.example                # 環境變數範例
```

---

## 3. 資料流

### 3.1 查詢流程

```
使用者輸入問題
    ↓
Streamlit Chat Page
    ↓ (httpx POST /api/v1/chat/query)
FastAPI Chat Router
    ↓
dependencies.py → get_search()
    ↓
core/search/ (向量搜尋 + 關鍵字搜尋)
    ↓
dependencies.py → get_ai_core()
    ↓
core/ai_core.py → OpenAI GPT-4o
    ↓
JSON Response → Streamlit 渲染
```

### 3.2 檔案自動入庫流程

```
使用者拖拽上傳 或 手動放入 data/raw_files/
    ↓
Watchdog FileSystemEventHandler (on_created)
    ↓ Debounce 2s
自動偵測文件類型 (_infer_doc_type)
    ↓
┌──────────────┬──────────────┐
│ 文字檔案      │ 圖片檔案      │
│ .md/.txt/.pptx│ .png/.jpg    │
├──────────────┼──────────────┤
│ core/         │ Gemini 2.0    │
│ ingestion_v3  │ Flash         │
│               │ → Markdown    │
│               │ → generated_md│
│               │ → ingestion   │
└──────┬───────┴──────┬───────┘
       ↓               ↓
   SQLite 入庫 (chunks, embeddings)
       ↓
   移至 archived_files/
   (失敗 → failed_files/)
```

---

## 4. API 總覽

| 路由 | 方法 | 說明 | 模組 |
|------|------|------|------|
| `/health` | GET | 健康檢查 | main.py |
| `/api/v1/chat/query` | POST | AI 問答 | chat.py |
| `/api/v1/ingestion/upload` | POST | 單檔上傳 | ingestion.py |
| `/api/v1/ingestion/upload_multiple` | POST | 批次上傳 | ingestion.py |
| `/api/v1/ingestion/status/{filename}` | GET | 處理狀態 | ingestion.py |
| `/api/v1/files/list` | GET | 檔案列表 | files.py |
| `/api/v1/files/download/{filename}` | GET | 檔案下載 | files.py |
| `/api/v1/admin/config` | GET/POST | 系統設定 | admin.py |
| `/api/v1/admin/stats` | GET | 統計資訊 | admin.py |
| `/api/v1/admin/documents` | GET | 文件列表 | admin.py |
| `/api/v1/admin/documents/{id}` | DELETE | 刪除文件 | admin.py |
| `/api/v1/admin/token_stats` | GET | Token 統計 | admin.py |
| `/api/v1/admin/batch/{action}` | POST | 批次操作 | admin.py |
| `/api/v1/search/semantic` | POST | 語意搜尋 | search.py |
| `/api/v1/search/keyword` | POST | 關鍵字搜尋 | search.py |

---

## 5. 技術棧

| 層級 | 技術 | 版本 |
|------|------|------|
| 後端框架 | FastAPI | ≥0.109 |
| ASGI Server | Uvicorn | ≥0.27 |
| 前端框架 | Streamlit | ≥1.30 |
| HTTP Client | httpx | ≥0.25 |
| 資料庫 | SQLite + sqlite-vec | - |
| 向量搜尋 | sqlite-vec | ≥0.1 |
| LLM | OpenAI GPT-4o | - |
| 圖片處理 | Google Gemini 2.0 Flash | - |
| 檔案監控 | Watchdog | ≥4.0 |
| 圖表 | Plotly | ≥5.18 |
| Mermaid | streamlit-mermaid | ≥0.1 |

---

## 6. 核心設計決策

### 6.1 core/ 保留在根目錄
- **原因**: 避免大規模重構風險，保持向後相容
- **方式**: `backend/app/dependencies.py` 透過 `sys.path` 注入引用
- **影響**: 舊版 `chat_app.py` / `admin_app.py` 仍可直接運作

### 6.2 全新資料庫
- **原因**: v2.0 表結構變更大 (10 張表 + 12 索引)，遷移成本 > 重建成本
- **檔案**: `knowledge_v2.db`, `tokenrecord_v2.db`
- **初始化**: `scripts/init_db.py`

### 6.3 前後端分離通訊
- **協定**: HTTP REST (JSON)
- **同步**: httpx (Streamlit 本身不支援 async)
- **好處**: 前端可替換 (未來 React / Vue)，後端可獨立部署

---

## 7. UI 優化項目

| # | 優化 | 頁面 | 狀態 |
|---|------|------|------|
| 1 | Tab 組織側邊欄 | Chat | ✅ |
| 2 | 快速操作按鈕 | Chat | ✅ |
| 3 | 卡片式搜尋結果 | Chat | ✅ |
| 4 | 載入動畫進度指示 | Chat | ✅ |
| 5 | Mermaid 圖表渲染 | Chat | ✅ |
| 6 | 拖拽上傳區 | Admin | ✅ |
| 7 | 實時處理進度 | Admin | ✅ |
| 8 | 批次操作列表 | Admin | ✅ |
| 9 | Token Plotly 互動圖表 | Admin, Stats | ✅ |
