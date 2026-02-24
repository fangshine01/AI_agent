# AI Expert System v1.5.0 🚀

一個基於 RAG (Retrieval-Augmented Generation) 的企業級知識管理專家系統，支援多格式文件解析、通用查詢引擎、AI 元數據提取與向量搜尋。

## 🌟 v1.5.0 新特性 (Current Version)

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

### 1. 安裝依賴

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

**v1.5.0** (2026-02)
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
