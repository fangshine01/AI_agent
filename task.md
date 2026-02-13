# Task Tracking - AI Expert System v2.3.0

## 實作進度追蹤

| # | 任務 | 狀態 | 建立/修改的檔案 |
|---|------|------|-----------------|
| 1 | 分析現有程式碼結構 | ✅ 完成 | - |
| 2 | WAL Mode + Chat History Schema | ✅ 完成 | `backend/app/utils/db_init.py` |
| 3 | 後端 Config 更新 | ✅ 完成 | `backend/config.py`, `.env.example` |
| 4 | Identity Middleware (BYOK) | ✅ 完成 | `backend/app/middleware/identity.py` (**新建**) |
| 5 | 安全驗證 Endpoint | ✅ 完成 | `backend/app/api/v1/auth.py` (**新建**) |
| 6 | Chat History API | ✅ 完成 | `backend/app/api/v1/history.py` (**新建**) |
| 7 | Error Handler + Health Check | ✅ 完成 | `backend/app/middleware/error_handler.py` (**新建**), `backend/app/api/v1/health.py` (**新建**) |
| 8 | Rate Limiting 中介層 | ✅ 完成 | `backend/app/middleware/rate_limiter.py` (**新建**), `backend/requirements.txt` |
| 9 | API Client 重構 (BYOK) | ✅ 完成 | `frontend/client/api_client.py` |
| 10 | Chat UI 重構 (歷史+驗證) | ✅ 完成 | `frontend/pages/1_💬_Chat.py` |
| 11 | main.py 路由註冊 | ✅ 完成 | `backend/app/main.py`, `backend/app/api/v1/__init__.py` |
| 12 | 啟動腳本 (.bat) | ✅ 完成 | `start_v2.2.bat` (**新建**), `stop_all.bat` (**新建**), `scripts/backup_db.bat` (**新建**) |
| 13 | 測試框架建立 | ✅ 完成 | `backend/tests/test_v2_2_features.py` (**新建**), `backend/tests/conftest.py` (**新建**), `pyproject.toml` (**新建**) |

## Phase 1 (P0) 實作完成摘要

### 新建檔案 (8 個)
1. `backend/app/middleware/identity.py` - BYOK 身份識別中介層
2. `backend/app/middleware/error_handler.py` - 全域錯誤處理中介層
3. `backend/app/middleware/rate_limiter.py` - 速率限制 (slowapi)
4. `backend/app/api/v1/auth.py` - API Key 驗證端點
5. `backend/app/api/v1/history.py` - 對話歷史 CRUD API
6. `backend/app/api/v1/health.py` - 增強版健康檢查
7. `start_v2.2.bat` / `stop_all.bat` / `scripts/backup_db.bat` - 啟動/停止/備份腳本
8. `backend/tests/test_v2_2_features.py` - v2.2.0 功能整合測試

### 修改檔案 (7 個)
1. `backend/app/utils/db_init.py` - WAL mode + chat_history/sessions 表
2. `backend/config.py` - AVAILABLE_MODELS, SESSION_TTL, RATE_LIMIT 設定
3. `.env.example` - 新增環境變數
4. `backend/requirements.txt` - 新增 slowapi 依賴
5. `frontend/client/api_client.py` - BYOK header 支援 + Auth/History 方法
6. `frontend/pages/1_💬_Chat.py` - BYOK 驗證流程 + 歷史管理 UI
7. `backend/app/main.py` - 新路由/中介層註冊

## Phase 2 (P1) 實作進度追蹤 — 性能與安全強化

| # | 任務 | 狀態 | 建立/修改的檔案 |
|---|------|------|-----------------|
| 14 | Retry 機制 (LLM + DB) | ✅ 完成 | `backend/app/utils/retry.py` (**新建**) |
| 15 | Session 管理器 | ✅ 完成 | `backend/app/utils/session_manager.py` (**新建**) |
| 16 | Token 多模型支援 | ✅ 完成 | `backend/app/middleware/token_tracker.py` (修改) |
| 17 | 結構化日誌系統 | ✅ 完成 | `backend/app/utils/logger.py` (**新建**) |
| 18 | Input 驗證中介層 | ✅ 完成 | `backend/app/middleware/validation.py` (**新建**) |
| 19 | Config 驗證 | ✅ 完成 | `backend/config.py` (修改) |
| 20 | GDPR 合規 API | ✅ 完成 | `backend/app/api/v1/user.py` (**新建**) |
| 21 | Admin UI 增強 | ✅ 完成 | `frontend/pages/2_📁_Admin.py` (修改) |
| 22 | 自動清理腳本 | ✅ 完成 | `scripts/cleanup.py` (**新建**) |
| 23 | 壓力測試腳本 (Locust) | ✅ 完成 | `tests/load_test.py` (**新建**) |
| 24 | NSSM 服務安裝腳本 | ✅ 完成 | `scripts/setup_service.bat` (**新建**) |

### Phase 2 新建檔案 (8 個)
1. `backend/app/utils/retry.py` - tenacity 重試裝飾器 (LLM 3次指數退避 / DB 5次固定等待)
2. `backend/app/utils/session_manager.py` - Session 生命週期管理 (TTL / 清理 / 統計)
3. `backend/app/utils/logger.py` - JSON 結構化日誌 + RotatingFileHandler (50MB×10)
4. `backend/app/middleware/validation.py` - 輸入驗證中介層 (XSS 防護 / Content-Length)
5. `backend/app/api/v1/user.py` - GDPR 合規 (資料匯出/刪除/個人統計)
6. `scripts/cleanup.py` - 自動清理 (Session/上傳/日誌/VACUUM)，排程用
7. `tests/load_test.py` - Locust 壓力測試 (50-100 並行使用者)
8. `scripts/setup_service.bat` - NSSM Windows 服務註冊 (互動式選單)

### Phase 2 修改檔案 (4 個)
1. `backend/app/middleware/token_tracker.py` - 新增 count_tokens() 多模型支援 + 圖片 Token 估算
2. `backend/config.py` - 新增 validate_config() 啟動時自動驗證
3. `frontend/pages/2_📁_Admin.py` - BYOK 驗證、By User Hash 統計、By Hour 圖表、系統健康頁
4. `backend/app/main.py` - 註冊 InputValidation 中介層 + user_router + setup_logging()

## Phase 3 (整合修復 + 完善) 實作追蹤

| # | 任務 | 狀態 | 建立/修改的檔案 |
|---|------|------|-----------------|
| 25 | Auth verify 狀態碼對齊 (ok→valid) | ✅ 完成 | `backend/app/api/v1/auth.py` (修改) |
| 26 | Token Stats API 格式對齊 | ✅ 完成 | `backend/app/api/v1/admin.py` (修改) |
| 27 | api_client 補 GDPR 方法 | ✅ 完成 | `frontend/client/api_client.py` (修改) |
| 28 | ai_core retry 例外過濾 | ✅ 完成 | `core/ai_core.py` (修改) |
| 29 | Admin UI GDPR 資料管理區 | ✅ 完成 | `frontend/pages/2_📁_Admin.py` (修改) |
| 30 | health.py 增強欄位 | ✅ 完成 | `backend/app/api/v1/health.py` (修改) |
| 31 | requirements.txt 補 tiktoken | ✅ 完成 | `backend/requirements.txt` (修改) |
| 32 | Task Scheduler 說明文件 | ✅ 完成 | `docs/scheduler.md` (**新建**) |
| 33 | 排程一鍵設定腳本 | ✅ 完成 | `scripts/setup_scheduler.bat` (**新建**) |

### Phase 3 修復摘要
1. **🔴 auth.py**: `VerifyResponse.status` 從 `"ok"` 改為 `"valid"`，與前端 Chat/Admin 一致
2. **🔴 admin.py**: `GET /token_stats` 回傳格式重構，新增 `summary`、`daily`、`by_model`、`by_user`、`by_hour`、`top_files` 欄位
3. **🔴 api_client.py**: 新增 `export_user_data()`、`delete_user_data()`、`get_user_stats()` 三個 GDPR 方法；`get_token_stats()` 改用 BYOK header + 解包 ResponseBase
4. **🟡 ai_core.py**: 4 處 `@retry` 加入 `retry_if_exception_type` 過濾（僅重試 Timeout/Connection/RateLimit 等暫時性錯誤）
5. **🟡 health.py**: 新增 `uptime_seconds`、`disk_free_gb`、`active_sessions`、`size_mb`、`file_count` 欄位
6. **🟡 Admin UI**: 系統健康 Tab 新增 GDPR 個人資料管理區（匯出/統計/刪除）
7. **🟢 requirements.txt**: 新增 `tiktoken>=0.7.0`
8. **🟢 docs/scheduler.md**: Windows Task Scheduler 完整設定指南
9. **🟢 scripts/setup_scheduler.bat**: 排程任務一鍵建立腳本

## Phase 4 (深度整合 + 部署完善) 實作追蹤

| # | 任務 | 狀態 | 建立/修改的檔案 |
|---|------|------|-----------------|
| 34 | 資料庫路徑統一 (root config → v2) | ✅ 完成 | `config.py` (修改), `scripts/cleanup.py` (修改), `scripts/backup_db.bat` (修改), `core/database/migrations/upgrade_schema.py` (修改) |
| 35 | 3_📊_Stats.py DB 路徑修正 | ✅ 完成 | `frontend/pages/3_📊_Stats.py` (修改) |
| 36 | 模型選擇器 13 模型 (含圖片模型) | ✅ 完成 | `backend/config.py` (修改: AVAILABLE_MODELS + MODEL_CATEGORIES + MODEL_COST_LABELS) |
| 37 | Models API 端點 | ✅ 完成 | `backend/app/api/v1/models.py` (**新建**), `backend/app/main.py` (修改: 註冊路由) |
| 38 | Auth verify 回傳結構化模型清單 | ✅ 完成 | `backend/app/api/v1/auth.py` (修改) |
| 39 | Chat UI 模型下拉選單 (顯示名+分類) | ✅ 完成 | `frontend/pages/1_💬_Chat.py` (修改) |
| 40 | api_client 全方法補 BYOK headers | ✅ 完成 | `frontend/client/api_client.py` (修改: 15+ 個方法) |
| 41 | 刪除舊版進入點 | ✅ 完成 | 刪除 `chat_app.py`, `admin_app.py`, `start_v2.bat`, `scripts/start_all.bat`, `tests/check_db_failed.py` |
| 42 | main.py 移除冗餘 root DB 初始化 | ✅ 完成 | `backend/app/main.py` (修改) |
| 43 | v1→v2 資料遷移腳本 | ✅ 完成 | `scripts/migrate_v1_to_v2.py` (**新建**) |
| 44 | 備份恢復測試腳本 | ✅ 完成 | `scripts/test_backup_recovery.py` (**新建**) |
| 45 | 部署文件與使用指南 | ✅ 完成 | `docs/deployment_guide.md` (**新建**) |
| 46 | .gitignore 建立 | ✅ 完成 | `.gitignore` (**新建**) |
| 47 | __pycache__ 全面清理 | ✅ 完成 | - |

### Phase 4 修復摘要
1. **🔴 DB 路徑統一**: root `config.py` 的 `DB_PATH`/`TOKEN_DB_PATH` 改指向 `backend/data/documents/knowledge_v2.db`，與 `backend/config.py` 一致
2. **🔴 模型選擇器**: `AVAILABLE_MODELS` 更新為 13 個模型（含 2 個圖片優化模型），新增 `MODEL_CATEGORIES` 分類標籤
3. **🔴 api_client BYOK**: chat(), upload_file(), upload_multiple_files(), get_config(), update_config() 等 15+ 個方法全部加入 `_build_headers()`
4. **🟡 Auth 結構化模型**: verify endpoint 回傳帶有 display_name/model_id/category/cost_label 的結構化清單
5. **🟡 Chat UI 下拉選單**: 顯示「💰 GPT-4.1 (Default High-end)」格式，內部提取 model_id 傳給後端
6. **🟠 舊檔清理**: 刪除 chat_app.py (847行), admin_app.py (442行), start_v2.bat, scripts/start_all.bat, tests/check_db_failed.py
7. **🟢 Phase 4 腳本**: migrate_v1_to_v2.py (遷移)、test_backup_recovery.py (恢復驗證)、deployment_guide.md (完整部署指南)

## 待進行 (Phase 5 - 長期優化)
- [x] 搜尋最佳化 (向量索引 / Embedding 快取 / 搜尋結果快取)
- [x] Prometheus Metrics 指標整合 (自製輕量收集器 + /metrics 端點)
- [x] E2E 端對端測試 (Playwright: Chat / Admin / API 健康)
- [x] API 文件完善 (OpenAPI docstring 13 個端點全數補齊)
- [x] 壓力測試 100 並發 (Locust + M4 驗收標準 + Search/Metrics 測試)
- [x] 並行運行觀察期文件 (2 週觀察清單)

## Phase 5 (長期優化) 實作追蹤

| # | 任務 | 狀態 | 建立/修改的檔案 |
|---|------|------|-----------------|
| 48 | UI Debug: 移除 API 提供者、更新模型選擇器 | ✅ 完成 | `frontend/pages/1_💬_Chat.py`, `frontend/pages/2_📁_Admin.py`, `frontend/client/api_client.py`, `frontend/components/uploader.py` |
| 49 | Admin 系統設定重寫 + 分析模式 | ✅ 完成 | `frontend/pages/2_📁_Admin.py`, `backend/app/api/v1/admin.py` |
| 50 | 後端 Auth 簡化 (移除 provider) | ✅ 完成 | `backend/app/api/v1/auth.py` |
| 51 | 舊版資料 / __pycache__ / 標記檔清理 | ✅ 完成 | 刪除: `data/knowledge.db`, `data/tokenrecord.db`, `.deps_installed*`, 16 個 `__pycache__/` |
| 52 | 過時模型參照更新 | ✅ 完成 | `backend/config.py`, `backend/app/core/image_processor.py`, `config.py` |
| 53 | Prometheus Metrics 中介層 | ✅ 完成 | `backend/app/middleware/monitoring.py` (**新建**), `backend/app/main.py` |
| 54 | 搜尋快取優化 (Embedding + 結果) | ✅ 完成 | `core/search/search_cache.py` (**新建**), `core/search/vector_search.py`, `core/search/__init__.py` |
| 55 | E2E 測試 (Playwright) | ✅ 完成 | `tests/e2e/conftest.py` (**新建**), `tests/e2e/test_chat_flow.py` (**新建**), `tests/e2e/test_admin_flow.py` (**新建**), `tests/e2e/test_health_api.py` (**新建**) |
| 56 | API 文件完善 (13 端點 docstring) | ✅ 完成 | `backend/app/api/v1/chat.py`, `ingestion.py`, `admin.py`, `search.py`, `history.py`, `user.py` |
| 57 | 壓力測試 100 並發增強 | ✅ 完成 | `tests/load_test.py` (新增 MetricsUser, SearchUser, ModelsUser + M4 驗收標準) |
| 58 | 並行運行觀察期文件 | ✅ 完成 | `docs/observation_checklist.md` (**新建**) |
| 59 | 版本號升級至 v2.3.0 | ✅ 完成 | `backend/app/main.py`, `frontend/pages/1_💬_Chat.py`, `frontend/pages/2_📁_Admin.py` |

### Phase 5 新建檔案 (7 個)
1. `backend/app/middleware/monitoring.py` - Prometheus Metrics 中介層 (計數器/直方圖/量規/錯誤率)
2. `core/search/search_cache.py` - LRU 快取 (Embedding 1000 筆 + 搜尋結果 200 筆, 5 分鐘 TTL)
3. `tests/e2e/conftest.py` - Playwright 測試 Fixtures
4. `tests/e2e/test_chat_flow.py` - Chat UI E2E 測試 (載入/側邊欄/互動)
5. `tests/e2e/test_admin_flow.py` - Admin UI E2E 測試 (載入/設定/Tab)
6. `tests/e2e/test_health_api.py` - API 端點健康測試 (/health + /metrics + /docs)
7. `docs/observation_checklist.md` - 2 週觀察期檢查清單

### Phase 5 修改檔案 (12 個)
1. `backend/app/main.py` - v2.3.0, 新增 Prometheus 中介層 + /metrics 路由
2. `frontend/pages/1_💬_Chat.py` - 移除 API 提供者, 13 模型 fallback
3. `frontend/pages/2_📁_Admin.py` - 移除 API 提供者, 系統設定重寫, 分析模式
4. `frontend/client/api_client.py` - 簡化 provider, 新增 analysis_mode
5. `frontend/components/uploader.py` - 新增 analysis_mode 參數
6. `backend/app/api/v1/auth.py` - v2.3.0, 移除 Gemini 專用驗證
7. `backend/app/api/v1/admin.py` - UpdateConfigRequest Pydantic, 完整 docstrings
8. `backend/app/api/v1/chat.py`, `ingestion.py`, `search.py`, `history.py`, `user.py` - 補齊 docstrings
9. `core/search/vector_search.py` - 整合 Embedding + 結果快取
10. `tests/load_test.py` - 100 並發增強 + M4 驗收標準
