# AI Expert System v2.0 - Backend

FastAPI 後端服務，提供 RESTful API 給前端呼叫。

## 架構

```
backend/
├── app/
│   ├── main.py              # FastAPI 入口 (lifespan, CORS, routes)
│   ├── dependencies.py      # 依賴注入 (橋接 core/ 模組)
│   ├── api/v1/              # API 路由
│   │   ├── chat.py          # POST /api/v1/chat/query
│   │   ├── ingestion.py     # POST /api/v1/ingestion/upload
│   │   ├── files.py         # GET  /api/v1/files/list
│   │   ├── admin.py         # GET  /api/v1/admin/stats
│   │   └── search.py        # POST /api/v1/search/semantic
│   ├── core/
│   │   └── image_processor.py  # Gemini 圖片→Markdown
│   ├── schemas/             # Pydantic v2 資料模型
│   ├── middleware/           # CORS, Token 追蹤
│   ├── services/
│   │   └── file_watcher.py  # Watchdog 檔案監控
│   └── utils/
│       └── file_handler.py  # 檔案工具
├── config.py                # 後端設定 (從 .env 讀取)
├── data/                    # 資料目錄
│   ├── raw_files/           # 待處理檔案 (放入即自動處理)
│   ├── archived_files/      # 處理完成歸檔
│   ├── generated_md/        # 圖片轉換的 Markdown
│   └── failed_files/        # 處理失敗的檔案
└── requirements.txt
```

## 啟動

```bash
# 安裝依賴
pip install -r backend/requirements.txt

# 初始化資料庫
python scripts/init_db.py

# 啟動
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

## API 文件

啟動後訪問: http://localhost:8000/docs (Swagger UI)

### 主要 API

| 路由 | 方法 | 說明 |
|------|------|------|
| `/health` | GET | 健康檢查 |
| `/api/v1/chat/query` | POST | AI 問答查詢 |
| `/api/v1/ingestion/upload` | POST | 上傳文件 |
| `/api/v1/ingestion/upload_multiple` | POST | 批次上傳 |
| `/api/v1/files/list` | GET | 檔案列表 |
| `/api/v1/admin/stats` | GET | 系統統計 |
| `/api/v1/admin/config` | GET/POST | 系統設定 |
| `/api/v1/admin/token_stats` | GET | Token 使用統計 |
| `/api/v1/search/semantic` | POST | 語意搜尋 |
| `/api/v1/search/keyword` | POST | 關鍵字搜尋 |

## 檔案監控

File Watcher 會自動監控 `data/raw_files/` 目錄:
- 放入檔案 → 自動偵測類型 → 入庫處理 → 移至 `archived_files/`
- 支援: `.md`, `.txt`, `.pptx`, `.ppt`, `.pdf`, `.png`, `.jpg`, `.jpeg`
- 圖片會先經過 Gemini 轉成 Markdown 再入庫
