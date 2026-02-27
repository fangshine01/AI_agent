# 最大化效益優化計畫 v3.1 — 已全部實施

> 更新日期：2026-02-24  
> 狀態：✅ **全部實施完成**  
> 目標 1：徹底消除 Streamlit 不必要刷新，提升操作流暢度  
> 目標 2：修復對話記錄無聲靜默失敗的 DB 儲存問題

---

## 一、DB 儲存稽核報告

### 問題嚴重度分析

| # | 位置 | 問題描述 | 嚴重度 |
|---|------|---------|-------|
| 1 | `Chat.py` `_save_message_to_history` | **所有錯誤完全靜默吞掉**：`client._request()` 自行 catch exception 並回傳 dict，外層的 `try/except` 根本捕不到任何 exception，使得 DB 存失敗時**零提示** | 🔴 高 |
| 2 | `Chat.py` `_save_message_to_history` | **回傳值未檢查**：即使後端回 `{"success": false, "message": "..."}` 也不處理，對話記錄靜默丟失 | 🔴 高 |
| 3 | `Chat.py` `_new_session` | Session 建立失敗時 `current_session_id` 保持 None，所有後續 save 靜默略過，整場對話不存入 DB | 🔴 高 |
| 4 | `backend/app/api/v1/chat.py` | `database.log_token_usage()` 若拋出例外，會造成 HTTP 500 中斷使用者的問答（應包 try/except） | 🟡 中 |
| 5 | `history.py` `save_message` | auto-title 邏輯讀取 message_count 時是在同一 transaction 的 UPDATE 之後（邏輯正確，但文件確認） | 🟢 已確認正常 |
| 6 | `db_init.py` | `sessions` 和 `chat_history` 均已在 `_upgrade_existing_db` 中 `CREATE TABLE IF NOT EXISTS`（舊版升級安全） | 🟢 已確認正常 |
| 7 | Token DB vs 知識庫 DB | `chat.py` 呼叫 `database.log_token_usage()` 寫入的是**知識庫 DB 中的 token_usage 備份表**，Token DB 另有獨立統計 — 雙重記錄，功能未衝突 | 🟢 已確認正常 |

### 修復方向

**`Chat.py` 修改（已實施）：**
```python
# 修改後的 _save_message_to_history
def _save_message_to_history(role: str, content: str, model_used: str = None, tokens_used: int = 0):
    """儲存對話訊息到後端，失敗時以 st.toast 通知（不阻擋 UI）"""
    if not st.session_state.current_session_id or not st.session_state.byok_verified:
        return
    try:
        result = client.save_message(
            session_id=st.session_state.current_session_id,
            role=role,
            content=content,
            model_used=model_used,
            tokens_used=tokens_used,
        )
        # 明確檢查回傳值，不再靜默略過錯誤
        if not result.get("success"):
            err = result.get("message", "未知錯誤")
            logger.warning(f"[DB] 訊息儲存未成功: {err}")
            st.toast(f"⚠️ 對話記錄未儲存: {err}", icon="⚠️")
    except Exception as e:
        logger.error(f"[DB] 儲存訊息例外: {e}")
        st.toast("⚠️ 對話記錄儲存失敗（網路或後端問題）", icon="⚠️")
```

**`chat.py` (backend) 修改（已實施）：**
```python
# log_token_usage 包裝以防 DB 失敗中斷問答
try:
    database.log_token_usage(file_name=None, operation="qa", usage=usage)
except Exception as e:
    logger.warning(f"[Token] 記錄 token 失敗（非致命）: {e}")
```

---

## 二、Streamlit 刷新最大化優化計畫（合併版）

> 一次升級至 Streamlit ≥ 1.37，同步取得 `st.form` + `@st.fragment` 全部效益

### 刷新觸發點清單

| 位置 | 觸發原因 | 嚴重程度 | 解法 |
|------|---------|---------|------|
| `Chat.py` Tab1 — API Key / Base URL / 使用者名稱 | 每個字元觸發全頁 rerun | 🔴 高 | `st.form` |
| `Admin.py` 側邊欄 — API Key / Base URL | 每個字元觸發全頁 rerun | 🔴 高 | `st.form` |
| `Chat.py` Tab2 — 產品型號 / 站點過濾輸入框 | 每個字元觸發 rerun | 🔴 高 | `st.form` |
| `Admin.py` Tab2 — 搜尋文件名篩選 | 每個字元觸發 rerun | 🟡 中 | `@st.fragment` |
| `Chat.py` Tab3 — Session 載入/刪除按鈕 | 每次點擊 `st.rerun()` 全頁刷 | 🟡 中 | `@st.fragment` |
| `Chat.py` 快速查詢 4 個按鈕 | 點擊觸發 rerun | 🟡 中 | `@st.fragment` |
| `Admin.py` Tab1 — 刪除文件按鈕 | `st.rerun()` 全頁刷 | 🟡 中 | `@st.fragment` |
| `Chat.py` Tab4 — `health_check()` | 每次 rerun 呼叫 API | 🟠 低 | `@st.cache_data(ttl=30)` |
| `Admin.py` 頂部 — `get_stats()` | 每次 rerun 呼叫 API | 🟠 低 | `@st.cache_data(ttl=60)` |
| `Admin.py` 側邊欄 — detailed health | 每次 rerun 呼叫 API | 🟠 低 | `@st.cache_data(ttl=30)` |

### 優化策略

#### 策略 A：`st.form` — 輸入框批次送出（消除逐鍵 rerun）

將多個輸入框包在 `st.form` 內，只有按下 Submit 才觸發 rerun：

```python
# Chat.py Tab1 修改範例
with st.form("byok_form", clear_on_submit=False):
    user_api_key = st.text_input("API Key", value=st.session_state.user_api_key, type="password")
    user_base_url = st.text_input("Base URL", value=st.session_state.user_base_url)
    user_name    = st.text_input("使用者名稱", value=st.session_state.user_name_input)
    submitted = st.form_submit_button("🔐 驗證 API Key", use_container_width=True)

if submitted:
    st.session_state.user_api_key    = user_api_key
    st.session_state.user_base_url   = user_base_url
    st.session_state.user_name_input = user_name
    if not user_api_key:
        st.error("請先輸入 API Key")
    else:
        _verify_and_set_identity(user_api_key, user_name, user_base_url)
        st.rerun()
```

> **注意**：模型 `selectbox` 放在 form 外（submit 邏輯之後）可保持即時切換。

#### 策略 B：`@st.cache_data` — 快取後端 API 呼叫（減少冗餘打後端）

```python
@st.cache_data(ttl=30)
def _cached_health_check(base_url: str) -> dict:
    """30 秒內重複 rerun 不重新打後端"""
    from client.api_client import APIClient
    return APIClient(base_url=base_url).health_check()

@st.cache_data(ttl=60)
def _cached_get_stats(base_url: str) -> dict:
    """60 秒 TTL 統計資料快取"""
    from client.api_client import APIClient
    return APIClient(base_url=base_url).get_stats()
```

手動刷新時加上 `.clear()` 強制清除快取。

#### 策略 C：`@st.fragment` — 局部重繪隔離（Streamlit ≥ 1.37 啟用）

Fragment 內的按鈕點擊不觸發**全頁** rerun，只重繪該 fragment 區塊：

```python
@st.fragment
def _render_session_list(chat_model: str):
    """Session 歷史列表 — 操作只重繪此區塊"""
    ...  # 載入/刪除邏輯移入此處

@st.fragment  
def _render_quick_buttons(display_options: dict):
    """快速查詢按鈕 — 模式切換只重繪此區塊"""
    ...

@st.fragment
def _render_document_manager(client):
    """Admin 文件管理 — 搜尋/刪除只重繪表格區塊"""
    ...
```

#### 策略 D：移除多餘 `st.rerun()` 呼叫

Streamlit Button 點擊本身即觸發一次 rerun，以下呼叫可移除：
- 快速查詢 4 個按鈕的 set session_state 後不需再額外 `st.rerun()`

---

### 預期效益

| 優化項目 | 說明 |
|---------|------|
| `st.form` API Key 輸入框 | 每次輸入流程節省 ~20-30 次 rerun |
| `st.form` 搜尋條件 | 每次輸入節省 ~5-10 次 rerun |
| `@st.cache_data` health/stats | 每次 rerun 節省 2-4 次後端 API 呼叫 |
| `@st.fragment` Session 列表 | Session 操作從全頁刷 → 局部重繪 |
| `@st.fragment` 文件管理 | 文件篩選從全頁刷 → 局部重繪 |
| `@st.fragment` 快速查詢按鈕 | 模式切換從全頁刷 → 局部重繪 |

---

## 三、注意事項

1. **`st.form` 限制**：form 內不可有即時更新的輸出元素，驗證狀態訊息需在 form 外顯示。

2. **`@st.fragment` 與 session_state**：fragment 可讀寫 `session_state`，但 fragment 外的 UI 不會因 fragment 內的 state 變更自動重繪——若對話記錄等主畫面需更新，fragment 內仍需呼叫 `st.rerun()`（觸發全頁）。

3. **`streamlit-mermaid` 相容性**：升版至 1.37 前，請先確認目前版本相容性（`pip show streamlit-mermaid`）。若有衝突，可升級至最新版本一同解決。

4. **手動刷新快取**：使用 `@st.cache_data` 時需注意手動刷新按鈕要呼叫快取函式的 `.clear()` 方法。

---

## 四、檔案修改清單

| 檔案 | 修改內容 | 狀態 |
|------|---------|------|
| `frontend/requirements.txt` | `streamlit>=1.30.0` → `streamlit>=1.37.0`（啟用 fragment） | ✅ |
| `backend/requirements.txt` | 同上，同步升版；更新其他套件版本 | ✅ |
| `backend/install.bat` | 新增前端安裝步驟、提示訊息優化 | ✅ |
| `frontend/pages/1_💬_Chat.py` | 修復 `_save_message_to_history` 錯誤處理；Tab1/Tab2 改 `st.form`；Tab3 改 `@st.fragment`；快速按鈕改 `@st.fragment`；快取 `health_check` | ✅ |
| `frontend/pages/2_📁_Admin.py` | 側邊欄改 `st.form`；文件管理改 `@st.fragment`；快取 `health_check` + `detailed_health` + `get_stats`；重新載入按鈕清除快取 | ✅ |
| `backend/app/api/v1/chat.py` | `log_token_usage` 包 try/except，防止 Token 記錄失敗中斷問答 | ✅ |
