# AI Agent 知識庫系統架構總覽 (v1.5.0)

本文檔詳細說明整個專案的目錄結構與每個程式檔案的功能，幫助開發者快速理解系統運作原理。

## 📁 專案根目錄

| 檔案 | 功能說明 |
|------|----------|
| `chat_app.py` | **問答前台 (Frontend)**<br>基於 Streamlit 的使用者介面，負責處理使用者對話、調用搜尋引擎、顯示參考來源與 AI 回答。v1.5.0 已整合 `universal_search`。 |
| `admin_app.py` | **管理後台 (Admin)**<br>基於 Streamlit 的管理介面，負責文件上傳、解析狀態監控、資料庫管理、Token 使用統計與系統設定。 |
| `config.py` | **全域配置 (Configuration)**<br>定義系統常數、環境變數載入、資料庫路徑、模型設定 (`gpt-4o`, `gpt-4o-mini`) 與 Logging 設定。 |
| `debug_search.py` | **除錯工具**<br>用於測試與診斷搜尋功能的獨立腳本，可直接執行各類搜尋函數 (Vector, Keyword, Hybrid) 並查看詳細輸出。 |
| `requirements.txt` | **依賴清單**<br>列出專案執行所需的所有 Python 套件 (如 `streamlit`, `openai`, `jieba`, `numpy`, `pymupdf` 等)。 |
| `README.md` | **專案說明**<br>專案的進入點，包含功能介紹、安裝指南、版本歷史與使用說明。 |

---

## 📂 Core 核心模組 (`core/`)

系統的核心邏輯層，負責協調各個子模組的運作。

| 檔案 | 功能說明 |
|------|----------|
| `__init__.py` | **模組導出**<br>定義 `core` 套件的公開介面，方便外部引用。 |
| `ai_core.py` | **AI 介面 (AI Wrapper)**<br>封裝 OpenAI API 呼叫，提供統一的 `analyze_slide` (圖文分析)、`get_embedding` (向量化) 與 `extract_keywords` (關鍵字提取) 函數。支援 retry 機制與錯誤處理。 |
| `ingestion_v3.py` | **文件攝取 (Ingestion)**<br>v1.5.0 文件處理核心。負責協調檔案讀取 (支援 PPTX, MD, TXT, PDF)、AI 元數據提取、解析器調用、向量化與寫入資料庫的完整流程。支援批次處理與進度回調。 |
| `metadata_extractor.py` | **元數據提取 (Metadata)**<br>使用 AI 或是規則自動從文件內容中提取摘要、分類、標籤、語言等元數據，並實作檔案雜湊 (Hash) 計算以避免重複上傳。 |
| `keyword_manager.py` | **關鍵字管理**<br>負責管理與載入特定領域的關鍵字詞典，用於提升關鍵字搜尋的準確度與分類識別。 |
| `ppt_parser.py` | **PPT 解析器**<br>專門處理 `.pptx` 檔案，使用 `python-pptx` 提取每一頁投影片的文字、備忘稿與圖片，並轉換為標準格式。 |
| `md_parser.py` | **Markdown 解析器**<br>處理 `.md` 檔案，解析章節結構與內容。 |

---

## 🔍 Search 搜尋模組 (`core/search/`)

v1.5.0 通用查詢引擎的核心實現，負責所有檢索相關邏輯。

| 檔案 | 功能說明 |
|------|----------|
| `__init__.py` | **搜尋介面**<br>統一導出所有搜尋相關功能，提供簡潔的 import 路徑。 |
| `universal_search.py` | **通用查詢引擎 (Universal Search)** (實作於 `query_router.py` 內)<br>v1.5.0 的單一入口點。負責接收查詢、分析意圖、自動選擇策略、執行搜尋並返回統一格式的結果。 |
| `query_router.py` | **查詢路由 (Router)**<br>實作 `analyze_query_intent` (意圖分析) 與 `select_search_strategy` (策略選擇)，決定如何處理使用者的問題。 |
| `reranker.py` | **重排序 (Reranker)**<br>實作 `semantic_rerank`，使用 AI 對初步搜尋結果進行語意相關性評分與重新排序，大幅提升準確度。也包含 `expand_query` (查詢擴展)。 |
| `vector_search.py` | **向量搜尋**<br>處理向量相似度計算 (Cosine Similarity)，執行純向量檢索。 |
| `legacy_search.py` | **關鍵字搜尋**<br>傳統的關鍵字匹配搜尋，支援多關鍵字 OR 邏輯、模糊比對與權重計分。 |
| `hybrid_search.py` | **混合搜尋**<br>結合向量搜尋與關鍵字搜尋的結果，使用 RRF (Reciprocal Rank Fusion) 演算法進行融合。 |
| `tokenizer.py` | **分詞工具**<br>使用 `jieba` 進行中文分詞，並處理英文單詞，優化搜尋關鍵字的切割。 |
| `keyword_matcher.py` | **關鍵字匹配**<br>提供高效的關鍵字比對邏輯，用於從文本中識別已知術語。 |

---

## 🗄️ Database 資料庫模組 (`core/database/`)

負責與 SQLite 資料庫的所有互動，封裝 SQL 操作。

| 檔案 | 功能說明 |
|------|----------|
| `__init__.py` | **資料庫介面**<br>導出常用的資料庫操作函數。 |
| `connection.py` | **連線管理**<br>管理 SQLite 資料庫連線，提供 Context Manager (`get_db_connection`) 確保連線正確關閉。 |
| `schema.py` | **結構定義**<br>定義資料庫與各個資料表 (Tables) 的 Schema 結構。 |
| `document_ops.py` | **文件操作**<br>實作 CRUD (Create, Read, Update, Delete) 操作，包括 `create_document_enhanced` (建立文件記錄)、`get_document` (查詢文件) 等。 |
| `vector_ops.py` | **向量操作**<br>負責 `vec_chunks` 表的操作，包括 `save_chunk_embedding` (儲存切片與向量) 與 `search_similar_chunks` (向量檢索)。 |
| `token_ops.py` | **Token 操作**<br>負責 `token_usage` 表的操作，記錄與查詢 API Token 的使用量。 |
| `migrations/upgrade_schema.py` | **資料庫遷移**<br>負責執行資料庫 Schema 的升級與變更，確保資料庫結構與程式碼版本同步。 |

---

## 📜 Parsers 解析器模組 (`core/parsers/`)

針對不同文件類型 (Knowledge, Training, Troubleshooting) 的特定解析邏輯。

| 檔案 | 功能說明 |
|------|----------|
| `base_parser.py` | **基礎解析器**<br>定義解析器的抽象基類 (Abstract Base Class)，規範 `parse` 方法的介面與通用邏輯 (如 JSON 提取)。 |
| `knowledge_parser.py` | **知識庫解析器**<br>繼承自 BaseParser。將文件拆解為「百科式知識卡片」，提取主題、定義、核心內容等。 |
| `training_parser.py` | **教育訓練解析器**<br>繼承自 BaseParser。將教材解析為教學大綱，提取適用對象、學習目標、測驗等。 |
| `troubleshooting_parser.py`| **異常解析器**<br>繼承自 BaseParser。將異常報告標準化為 6 大欄位 (問題描述、真因、對策等)。 |

---

## 🔄 資料流向 (Data Flow)

### 1. 文件上傳流程
`admin_app.py` -> `ingestion_v3.py` -> `metadata_extractor.py` (提取元數據) -> `parsers/` (解析內容) -> `ai_core.py` (向量化) -> `database/` (存入 DB)

### 2. 查詢檢索流程
`chat_app.py` -> `search.universal_search` -> `query_router.py` (意圖/策略) -> `vector_search/legacy_search` (檢索) -> `reranker.py` (重排序) -> `chat_app.py` (顯示結果) -> `ai_core.py` (生成回答)

---

## ⚠️ 特別說明

- **v1.5.0 變更**: 系統已全面導入 `core/search/` 下的新模組，舊有的搜尋邏輯 (`search_v2.py`, `search_old.py` 若存在) 已被標記為 Deprecated 或移除。
- **資料庫**: 使用 `sqlite-vec` (或相容的向量儲存方案) 進行向量存儲，所有資料庫操作應透過 `core.database` 模組進行，嚴禁直接在 UI 層執行 SQL。
