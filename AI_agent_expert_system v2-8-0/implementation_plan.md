# 程式碼重構與拆分規劃 (逾 300 行之模組)

## 背景描述
本專案中有部分程式碼檔案長度超過 300 行（高達 600-700 行），導致閱讀、維護與擴充上較為困難。
此計畫的主要目標，是將這些巨型檔案按照「單一職責原則 (SRP)」、「關注點分離」以及「模組化」等設計模式進行拆分整理，讓後續的開發與除錯更有效率。

## ✅ Frontend Refactoring — 已完成 (v4.0)

> 以下 Frontend 拆分已全數完成，導入 Streamlit 1.50+ 新 API 與 `.github/skills` 最佳實踐。

### ✅ `frontend/client/api_client.py` (567 → 35 行 facade)
- **已完成**: 使用 Python MRO 多重繼承拆為 3 個領域模組
- `client/base_client.py` (~105 行) — BaseClient：HTTP、auth、headers
- `client/chat_client.py` (~200 行) — ChatClient：chat, verify, sessions, search
- `client/admin_client.py` (~200 行) — AdminClient：config, stats, docs, tokens, ingestion, GDPR
- `client/api_client.py` (35 行) — `APIClient(ChatClient, AdminClient)` 向後相容 facade

### ✅ `frontend/app_pages/admin.py` (681 → 183 行 orchestrator)
- **已完成**: 拆為 5 個 component 模組
- `components/admin/doc_manager.py` — @st.fragment 文件管理（搜尋/過濾/排序/刪除）
- `components/admin/token_charts.py` — Token 統計 KPI + Plotly 圖表
- `components/admin/health_monitor.py` — 系統健康監控（版本/Uptime/磁碟/DB）
- `components/admin/config_form.py` — 系統設定表單（st.segmented_control 取代 st.radio）
- `components/admin/gdpr_panel.py` — GDPR 資料管理面板

### ✅ `frontend/app_pages/chat.py` (483 → 185 行 orchestrator)
- **已完成**: 拆為 3 個 component 模組
- `components/chat/handlers.py` (~120 行) — 業務邏輯（驗證、Session CRUD、訊息儲存、stream）
- `components/chat/session_list.py` (~70 行) — @st.fragment 對話歷史列表
- `components/chat/sidebar_config.py` (~170 行) — 側邊欄 4-tab 配置（BYOK/搜尋/歷史/狀態）
- 搜尋情境選擇: st.segmented_control 取代 st.radio
- 模糊搜尋: st.toggle 取代 st.checkbox

### ✅ `frontend/app_pages/stats.py` (403 → 65 行 orchestrator)
- **已完成**: 拆為 5 個 @st.fragment component 模組
- `components/stats/health_metrics.py` — 系統健康（run_every=30s, border=True metrics）
- `components/stats/doc_overview.py` — 文件概覽（run_every=300s, Plotly 圖表）
- `components/stats/token_charts.py` — Token 分析（run_every=60s, 趨勢/模型/操作分佈）
- `components/stats/search_analytics.py` — 搜尋分析（run_every=60s, 熱門查詢圖表）
- `components/stats/system_resources.py` — 系統資源（run_every=300s, 磁碟/檔案統計）
- 時間範圍選擇: st.segmented_control 取代 st.selectbox

### ✅ 全域 1.50+ 現代化
- `use_container_width=True` → `width="stretch"` (35 處，跨 6 個檔案)
- `use_container_width=False` → `width="content"` (如適用)
- `st.markdown("---")` → `st.divider()` (所有活躍檔案)
- Emoji → Material icons (`:material/icon_name:`)
- `st.metric(..., border=True)` 加框 KPI 卡片
- `st.container(horizontal=True)` 水平按鈕群組
- `st.badge()` 狀態標籤
- `st.container(border=True)` 卡片化資訊區塊

### ✅ `frontend/Home.py` 現代化
- 完全重寫為 `st.navigation` + `st.Page` API (~40 行)
- 使用 Material icons 與 sections 分組
- 舊 `frontend/pages/` 目錄已刪除 (消除 36+ `use_container_width` 警告)

---

## ✅ Backend Components — 已完成

### ✅ `backend/app/api/v1/admin.py` (431 → ~260 行)
- **已完成**: 將 Token 統計計算抽出至 Service 層
- `backend/app/services/token_stats_service.py` (~170 行) — `build_enhanced_token_stats()` + 7 私有 SQL 查詢輔助函數
- `admin.py` 保留為薄 Router，僅做參數驗證與路由

### ✅ `backend/app/api/v1/history.py` (420 → ~155 行)
- **已完成**: 全部 raw sqlite3 操作抽出至 Service 層
- `backend/app/services/history_service.py` — `list_sessions()`, `create_session()`, `get_session_history()`, `delete_session()`, `update_session_title()`, `save_message()`
- `backend/app/schemas/history.py` — 6 個 Pydantic models: `CreateSessionRequest`, `SessionInfo`, `SessionListResponse`, `ChatMessage`, `SaveMessageRequest`, `SessionHistoryResponse`
- `history.py` 保留為薄 Router，委派至 Service + Schemas

### ✅ `backend/app/utils/db_init.py` (DDL 去重)
- **已完成**: DDL 定義去重為模組級常數（單一真實來源）
- `_DOCUMENTS_DDL`, `_VEC_CHUNKS_DDL`, `_CHAT_HISTORY_DDL`, `_SESSIONS_DDL` 等常數
- `_execute_ddl()` 輔助函數
- `_KNOWLEDGE_INDEXES` / `_TOKEN_INDEXES` 清單
- `_init_knowledge_db` 與 `_upgrade_existing_db` 共用同一組常數

---

## ✅ Core Components — 已完成

### ✅ `core/ai_core.py` (511 → 25 行 facade)
- **已完成**: 拆為 5 個子模組 + facade 重新匯出
- `core/llm_client.py` — `call_chat_model()`, `encode_image_to_base64()`, `RETRYABLE_EXCEPTIONS` — HTTP 傳輸層
- `core/slide_analyzer.py` — `analyze_slide()`, `_analyze_text_only()`, `_analyze_with_vision()` — @retry 裝飾器
- `core/embedding.py` — `get_embedding()` — httpx embedding API + retry
- `core/chat.py` — `chat_response()`, `_build_rag_prompt()`, `_build_fallback_prompt()` — RAG Q&A
- `core/keyword_extractor.py` — `extract_keywords()` — LLM 關鍵字提取 + retry
- `core/ai_core.py` (25 行) — facade 重新匯出所有公開 API

### ✅ `core/ingestion_v3.py` (688 → ~380 行)
- **已完成**: 抽出 3 個子模組至 `core/ingestion/` 套件
- `core/ingestion/__init__.py` — 套件初始化
- `core/ingestion/file_reader.py` — `read_file_content()`, `extract_chapters()` — .txt/.md/.pptx/.pdf
- `core/ingestion/keyword_matcher.py` — `save_keywords_to_db()` — keyword_mappings 文字匹配 + AI metadata
- `core/ingestion/image_ingestion.py` — `process_image_with_gemini()` — Gemini Vision pipeline
- 修復 raw SQL bypass (原第 150-162 行): 改用 `database.update_document()` 取代 `sqlite3.connect` 直接操作

### ✅ `core/database/document_ops.py` (523 → ~426 行)
- **已完成**: 函數整合與去重
- `create_document` 整合為 `create_document_enhanced` 的薄 wrapper
- `log_search_history` 已棄用，委派至 `metadata_ops.log_search_analytics`
- 重複的 `get_chunks_by_doc_id` 移除，改為從 `vector_ops` 重新匯出
- `update_document` allowed_fields 擴充: `parent_doc_id`, `source_type`, `status`

### ✅ `core/database/metadata_ops.py` (438 → ~249 行)
- **已完成**: 拆為 2 個專責子模組 + 向後相容重新匯出
- `core/database/version_ops.py` — `create_version()`, `get_document_versions()` — document_versions 表操作
- `core/database/analytics_ops.py` — `log_search_analytics()`, `update_search_feedback()`, `get_search_stats()` — search_analytics 表操作
- `metadata_ops.py` 保留 troubleshooting/procedure/chunk metadata，並透過重新匯出維持向後相容
- `core/database/__init__.py` 更新為直接從新模組匯入

### ✅ `core/search/query_router.py` (690 → ~248 行 orchestrator)
- **已完成**: 拆為 3 個子模組，query_router 保留為 orchestrator
- `core/search/intent_analyzer.py` — `QueryIntent`/`SearchStrategy` 列舉 + `analyze_query_intent()` + `select_search_strategy()`
- `core/search/troubleshooting_matcher.py` — `try_exact_troubleshooting_match()` + `_extract_ts_keywords_from_query()`
- `core/search/post_processor.py` — `post_process_results()` + `calculate_confidence()` + `is_cross_query()`
- `query_router.py` 保留: `universal_search()`, `_should_skip_llm()`, `_execute_search()`, `_log_search_history()`

---

## Verification Plan
1. **重構後單元測試**: 確保所有的 `import` 都更新到新路徑，啟動後端時無 `ModuleNotFoundError`。
2. **端到端手動驗證**: 
   - 確保 Streamlit 前端 (Chat, Admin, Stats) 全部頁面功能顯示正常、圖表正確。
   - 驗證後端 API 及 Core 元件依然能正常新增文件、順利檢索、及歷史詢問不崩潰。
