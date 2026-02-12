# AI Expert System v2.0 - Frontend

Streamlit 多頁面前端應用，透過 HTTP 呼叫 FastAPI 後端。

## 架構

```
frontend/
├── Home.py                  # 首頁入口 (系統狀態 + 導航)
├── config.py                # API 連線設定
├── pages/
│   ├── 1_💬_Chat.py         # 專家問答介面
│   ├── 2_📁_Admin.py        # 管理後台 (上傳/文件/設定/Token)
│   └── 3_📊_Stats.py        # 統計儀表板
├── client/
│   └── api_client.py        # HTTP API 客戶端
├── components/
│   ├── chat_ui.py           # 聊天 UI 元件 (卡片式結果, 8D, Troubleshooting)
│   └── uploader.py          # 拖拽上傳元件
└── utils/
    └── markdown_renderer.py # Mermaid + Markdown 渲染
```

## UI 優化

已實作的優化建議:

| # | 優化項目 | 對應頁面 |
|---|---------|---------|
| 建議 1 | Tab 組織側邊欄 | Chat |
| 建議 2 | 快速操作按鈕 | Chat |
| 建議 3 | 卡片式搜尋結果 | Chat |
| 建議 4 | 載入動畫與進度指示 | Chat |
| 建議 5 | Mermaid 圖表渲染 | Chat |
| 建議 6 | 拖拽上傳區 | Admin |
| 建議 7 | 實時處理進度 | Admin |
| 建議 8 | 批次操作列表 | Admin |
| 建議 9 | Token 互動式圖表 (Plotly) | Admin, Stats |

## 啟動

```bash
# 確保後端已啟動 (port 8000)
pip install -r frontend/requirements.txt
streamlit run frontend/Home.py --server.port 8501
```

## 設定

前端透過 `frontend/config.py` 設定 API 位址，預設 `http://localhost:8000`。
可在 `.env` 中設定 `API_BASE_URL` 覆蓋。
