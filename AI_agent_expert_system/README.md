# AI Expert System v2.0.0 🚀

一個基於 RAG (Retrieval-Augmented Generation) 的企業級知識管理專家系統，支援多格式文件解析、通用查詢引擎、AI 元數據提取與向量搜尋。

## 🌟 v2.0.0 新特性 (Current Version)

### 🏗️ 前後端分離架構
- **FastAPI 後端**: RESTful API、Swagger 文件、Token 追蹤中介層
- **Streamlit 前端**: 多頁面應用、Tab 組織、卡片式 UI
- **HTTP 通訊**: httpx 非同步客戶端，前端不再直接呼叫 core 模組

### 📡 檔案監控服務 (File Watcher)
- **Watchdog 監控**: 自動偵測 `data/raw_files/` 新檔案
- **自動入庫**: 偵測類型 → 處理 → 歸檔，零人工干預
- **圖片轉換**: Gemini 2.0 Flash 將圖片轉為 Markdown (表格/流程圖/架構圖)

### 🎨 UI 全面優化
- Tab 組織側邊欄、快速操作按鈕、卡片式搜尋結果
- 載入動畫/進度指示、Mermaid 圖表渲染
- 拖拽上傳、批次操作、Plotly 互動圖表

### 📊 統計儀表板
- 系統健康監控、文件類型分佈、Token 使用趨勢
- 搜尋分析、熱門查詢、系統資源狀態

---

## 🌟 v1.5.0 特性

### 🔍 通用查詢引擎 (Universal Query Engine)
- **智慧意圖分析**: 自動識別查詢類型 (事實/步驟/問題排查/比較/文件查找)
- **自動策略選擇**: 根據查詢特徵選擇最佳搜尋策略 (向量/關鍵字/混合/檔名優先/深度語意)
- **AI 重排序**: 使用 GPT 重新排序結果，提升準確度 20-30%
- **查詢擴展**: 自動生成語意相近的查詢變體

### 📊 智慧元數據提取 (Smart Metadata)
- **AI 自動摘要**: 使用 GPT 提取文件摘要和重點
- **自動分類標籤**: AI 推薦分類和關鍵標籤
- **重複檢測**: 基於檔案 hash 避免重複上傳

### 🗄️ 增強資料庫結構
- **24+ 個新欄位**: category, tags, file_hash, summary, priority 等
- **2 個新表**: document_relations, search_history
- **10 個索引**: 優化查詢效能

### 🎯 搜尋系統改善
- **召回率提升 80%+**: 從 0% 提升到 80%+
- **多關鍵字 OR 搜尋**: 支援部分匹配
- **智慧分詞**: 處理中英文混合查詢

---

## ✨ 主要功能

### 1. 多格式文件支援
- **支援格式**: PPTX, Markdown, Text, PDF (NEW!)
- **自動解析**: 智慧提取文字、表格與圖片內容 (PPTX/PDF)
- **結構化處理**: 將非結構化文件轉為結構化知識單元

### 2. 專業知識分類
系統支援四種專屬文件類型，針對不同場景優化：
- **📚 知識庫 (Knowledge)**: 技術文件、手冊、教科書 (著重章節結構)
- **🎓 教育訓練 (Training)**: 培訓教材、課程講義 (著重重點摘要)
- **📋 日常手順 (Procedure)**: SOP、操作手冊 (著重步驟分解)
- **🔧 異常解析 (Troubleshooting)**: 8D 報告、維修記錄 (著重問題分析與解決對策)

### 3. 雙介面設計
- **⚙️ 管理後台 (Admin Console)**: 文件上傳、解析狀態監控、資料庫管理、Token 使用統計
- **💬 專家問答 (Chat Expert)**: 智慧搜尋、多輪對話、模糊比對糾錯、自動萃取關鍵字

### 4. 智慧搜尋引擎
- **通用查詢引擎**: 自動選擇最佳策略 (Vector/Metric/Hybrid)
- **多層級降級搜尋**: 檔名搜尋 -> 關鍵字搜尋 -> 摘要搜尋 -> 全文搜尋
- **智慧萃取**: 自動從自然語言中提取檔名或編號

---

## 🚀 快速開始

### v2.0 (前後端分離)

```bash
# 一鍵啟動
scripts\start_all.bat

# 或分別啟動
scripts\start_backend.bat   # 後端 → http://localhost:8000/docs
scripts\start_frontend.bat  # 前端 → http://localhost:8501
```

### v1.x (Legacy 單體模式)

仍可使用舊版，核心模組未更動：

```bash
pip install -r requirements.txt
```

### 2. 啟動系統

**啟動問答介面 (Port 8502)**
```bash
streamlit run chat_app.py
```

**啟動管理後台 (Port 8501)**
```bash
streamlit run admin_app.py
```

---

## 📚 文檔

- [API 使用文檔](docs/API_USAGE.md) - 完整 v1.5.0 API 參考和使用範例
- [系統架構總覽](docs/ARCHITECTURE_OVERVIEW.md) - v1.5.0 架構與檔案功能說明
- [檔案格式指南](docs/FILE_FORMATS.md) - 支援格式 (含 PDF) 與撰寫規範
- [新手入門指南](docs/BEGINNER_GUIDE.md) - 🔰 小白專用的 Step-by-Step 教學
- [技術科普](docs/VECTOR_DB_INTRO.md) - 向量資料庫與 OpenAI Embeddings 介紹
- [實作總結](walkthrough.md) - 開發歷程和技術細節
- [任務清單](task.md) - 功能開發進度

---

## 📝 版本資訊

**v2.0.0** (2025-06)
- 🏗️ 前後端分離: FastAPI + Streamlit 多頁面
- 📡 Watchdog 檔案監控: 自動入庫
- 🖼️ Gemini 圖片處理: 圖片→Markdown
- 🎨 UI 優化: Tab/卡片/進度/Mermaid/Plotly
- 📊 統計儀表板: 完整系統監控
- 🚀 部署腳本: start_all.bat 一鍵啟動

**v1.5.0** (2025-02)
- 🚀 通用查詢引擎: 智慧意圖分析與自動策略選擇
- 🤖 AI 元數據提取: 自動摘要、分類、標籤
- 📊 資料庫結構增強: 24+ 新欄位、2 個新表、10 個索引
- 🎯 搜尋系統改善: 召回率提升 80%+
- 📂 新增 PDF 支援
- 📚 完整 API 文檔: 詳見 `docs/API_USAGE.md`

**Pre-v1.5.0 History**
- 向量搜尋引擎: 支援語意搜尋
- 混合搜尋: 結合向量和關鍵字
- Embedding 支援: 使用 OpenAI text-embedding-3-small
- 架構重構: 拆分為 Admin/Chat 雙介面
- 資料庫升級: 支援 Knowledge/Training/Procedure/Troubleshooting 四大分類
