# 任務追蹤 — AI Expert System 優化

> 更新日期：2026-02-24

## 已完成 ✅

### Phase 1: DB 儲存修復
- [x] `Chat.py` `_save_message_to_history` — 明確檢查回傳值 + `st.toast` 提示
- [x] `Chat.py` `_new_session` — 失敗時 toast 警告，不再靜默略過
- [x] `backend/app/api/v1/chat.py` — `log_token_usage` 加 try/except（×2 處）

### Phase 2: 依賴與安裝更新
- [x] `frontend/requirements.txt` — streamlit>=1.37.0（啟用 @st.fragment）
- [x] `backend/requirements.txt` — 同步升版 + 整理分類
- [x] `backend/install.bat` — 重寫為 4 步驟安裝流程

### Phase 3: Streamlit 刷新優化
- [x] `Chat.py` Tab1（連線）— 3 個 text_input 改 `st.form("byok_form")`
- [x] `Chat.py` Tab2（搜尋）— 產品/站點過濾改 `st.form("search_filter_form")`
- [x] `Chat.py` Tab3（歷史）— Session 列表改 `@st.fragment`
- [x] `Chat.py` Tab4（狀態）— health_check 改 `@st.cache_data(ttl=30)`
- [x] `Chat.py` 快速查詢按鈕 — 4 個按鈕改 `@st.fragment`
- [x] `Admin.py` 側邊欄 — API Key/Base URL 改 `st.form("admin_byok_form")`
- [x] `Admin.py` 側邊欄 — health_check 改 `@st.cache_data(ttl=30)`
- [x] `Admin.py` 側邊欄 — detailed_health 改 `@st.cache_data(ttl=30)`
- [x] `Admin.py` 頂部統計 — get_stats 改 `@st.cache_data(ttl=60)`
- [x] `Admin.py` Tab2（文件管理）— 搜尋/刪除改 `@st.fragment`
- [x] `Admin.py` 重新載入按鈕 — 加入 `.clear()` 清除所有快取
- [x] `implementation_plan.md` 更新至 v3.1（標記全部實施完成）

## 待辦 📋

_（目前無待辦項目）_
