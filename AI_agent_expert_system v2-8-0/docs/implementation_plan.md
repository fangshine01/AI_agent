# AI Agent Expert System — 優化計畫 v4.0

> 建立日期：2026-02-27  
> 狀態：✅ **已完成實施**  
> 前提：v3.1 所有項目已全數完成（`@st.fragment`、`@st.cache_data`、`st.form`、DB 儲存稽核）

---

## 概覽

| # | 任務 | 影響範圍 | 優先度 |
|---|------|---------|-------|
| 1 | 對話系統依 skills 全面優化 | `frontend/` Chat 頁面 | 🔴 高 |
| 2 | 頁面預渲染與快取強化 | `frontend/` 所有頁面 | 🔴 高 |
| 3 | 程式碼架構重組 | `frontend/` 整體目錄結構 | 🟡 中 |
| 4 | Admin + Stats 分離為獨立 Port，加入登入頁 | `frontend/` + `scripts/` | 🟡 中 |

---

## 任務一：對話系統優化（依 `building-streamlit-chat-ui` skill）

### 1.1 問題現況

| 問題 | 位置 | 描述 |
|------|------|------|
| 無 streaming response | `1_💬_Chat.py` | AI 回答是一次性顯示，未使用 `st.write_stream`，使用者需等待完整回答才看到輸出 |
| 缺少 suggestion chips | `1_💬_Chat.py` | 第一次進入聊天無引導提示，使用者不知從何問起 |
| feedback 按鈕缺失 | `1_💬_Chat.py` | AI 回答後沒有 👍/👎 回饋機制 |
| 清除對話按鈕缺失 | `1_💬_Chat.py` | 沒有 "Clear chat" 功能，舊訊息無法快速清除 |
| `messages` 初始化分散 | `1_💬_Chat.py` | Session state 初始化分散在各處，非集中 `setdefault` 模式 |
| 對話泡泡缺少自訂 avatar | `1_💬_Chat.py` | 目前用預設 avatar，可加入品牌 icon 增進識別性 |

### 1.2 優化方案

#### (A) 啟用 Streaming Response

```python
# 舊：一次性顯示
response = client.ask(question=prompt, ...)
with st.chat_message("assistant", avatar=":material/support_agent:"):
    st.markdown(response["answer"])

# 新：st.write_stream
with st.chat_message("assistant", avatar=":material/support_agent:"):
    response = st.write_stream(client.ask_stream(question=prompt, ...))
st.session_state.messages.append({"role": "assistant", "content": response})
```

> **後端需配合**：`APIClient.ask_stream()` 需串接 FastAPI 的 StreamingResponse，以 `text/event-stream` 格式回傳。若後端尚未支援，先以 generator wrap 現有 response 模擬逐字輸出（降級處理）。

#### (B) Suggestion Chips（首次進入引導）

```python
SUGGESTIONS = {
    ":blue[:material/build:] 查 SOP 步驟": "請列出XX製程的標準作業步驟",
    ":orange[:material/search:] 查故障排除": "這個錯誤碼代表什麼意思？",
    ":green[:material/description:] 查技術文件": "找出關於XX的技術規範",
    ":purple[:material/history:] 查歷史案例": "有沒有類似問題的處理案例？",
}

if not st.session_state.messages:
    selected = st.pills(
        "快速開始：",
        list(SUGGESTIONS.keys()),
        label_visibility="collapsed",
    )
    if selected:
        prompt = SUGGESTIONS[selected]
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()
```

#### (C) 訊息 Feedback（最後一條 AI 訊息）

```python
with st.chat_message("assistant", avatar=":material/support_agent:"):
    st.markdown(msg["content"])
    if i == len(st.session_state.messages) - 1:
        feedback = st.feedback("thumbs")
        if feedback is not None:
            st.toast("感謝您的回饋！" if feedback == 1 else "感謝！我們會繼續改善。", icon="🙏")
```

#### (D) 集中 Session State 初始化

```python
# 頁面頂部統一初始化（依 using-streamlit-session-state skill）
_SS_DEFAULTS = {
    "messages": [],
    "session_tokens": 0,
    "byok_verified": False,
    "byok_user_hash": "",
    "current_session_id": None,
    "session_list": [],
    "user_api_key": "",
    "user_base_url": "http://innoai.cminl.oa/agency/proxy/openai/platform",
    "user_name_input": "",
    "chat_model": None,
}
for k, v in _SS_DEFAULTS.items():
    st.session_state.setdefault(k, v)
```

#### (E) 自訂 Avatar + Clear Chat 按鈕

```python
# Avatar
with st.chat_message("user",      avatar=":material/person:"): ...
with st.chat_message("assistant", avatar=":material/support_agent:"): ...

# Clear Chat
def _clear_chat():
    st.session_state.messages = []
    st.session_state.current_session_id = None
    st.session_state.session_tokens = 0

st.button(":material/delete_sweep: 清除對話", on_click=_clear_chat, use_container_width=True)
```

### 1.3 修改清單

| 檔案 | 修改項 |
|------|--------|
| `frontend/app_pages/chat.py`（重命名後） | 全部 (A)–(E) |
| `frontend/client/api_client.py` | 新增 `ask_stream()` 方法 |
| `backend/app/api/v1/chat.py` | 新增 `/ask/stream` endpoint（`StreamingResponse`） |

---

## 任務二：頁面預渲染與快取強化（依 `optimizing-streamlit-performance` skill）

### 2.1 現況分析

| 位置 | 問題 | 嚴重度 |
|------|------|-------|
| `3_📊_Stats.py` 整頁 | 無任何 `@st.fragment`，每次點擊重繪整張 Stats 頁 | 🔴 高 |
| `3_📊_Stats.py` 圖表區 | `health_check()` 和 `get_token_stats()` 無快取，每次 rerun 都打後端 | 🔴 高 |
| `3_📊_Stats.py` auto_refresh | 使用全頁 `st.rerun()`，效能浪費 | 🟡 中 |
| `2_📁_Admin.py` 文件列表 | `list_documents()` 在 Fragment 內但無快取 | 🟡 中 |
| 模型清單重複 | Chat 和 Admin 各有一份 ~30 個模型定義（共 ~120 行重複代碼） | 🟡 中 |
| 快取函式分散 | `_cached_health_check` 等各頁面各自定義，難以維護 | 🟠 低 |

### 2.2 優化方案

#### (A) Stats 頁面完整 Fragment 化（含 auto-refresh）

```python
@st.fragment(run_every="30s")
def _render_health_metrics():
    health = cached_health_check(API_BASE_URL)
    # ... metrics ...

@st.fragment(run_every="60s")
def _render_token_charts():
    token_data = cached_token_stats(API_BASE_URL)
    # ... plotly charts ...

@st.fragment(run_every="300s")
def _render_doc_overview():
    stats = cached_get_stats(API_BASE_URL)
    # ... 文件類型圖表 ...
```

使用 `run_every` 取代全頁 `st.rerun()` auto-refresh，各區塊獨立更新。

#### (B) 集中快取函式至 `utils/cache.py`

```python
# utils/cache.py
@st.cache_data(ttl="30s", max_entries=10)
def cached_health_check(base_url: str) -> dict: ...

@st.cache_data(ttl="30s", max_entries=10)
def cached_detailed_health(base_url: str) -> dict: ...

@st.cache_data(ttl="60s", max_entries=10)
def cached_get_stats(base_url: str) -> dict: ...

@st.cache_data(ttl="60s", max_entries=10)
def cached_token_stats(base_url: str) -> dict: ...

@st.cache_data(ttl="120s", max_entries=5)
def cached_list_documents(base_url: str) -> list: ...

@st.cache_resource
def get_api_client(base_url: str) -> APIClient: ...
```

加入 `max_entries` 防止快取無限成長。

#### (C) 手動刷新清除快取

```python
if st.button(":material/refresh: 立即刷新"):
    cached_health_check.clear()
    cached_get_stats.clear()
    cached_token_stats.clear()
    st.rerun()
```

#### (D) 模型清單提取至 `utils/models.py`

```python
# utils/models.py — 唯一定義，Chat + Admin 共用
AVAILABLE_MODELS: list[dict] = [
    {"display_name": "OpenAI-GPT-4o", "model_id": "gpt-4o",
     "category": "OpenAI 標準", "cost_label": "💰💰"},
    # ... 全部 27 個模型 ...
]
```

### 2.3 修改清單

| 檔案 | 動作 |
|------|---------|
| `frontend/utils/cache.py` | 新增：集中快取函式 |
| `frontend/utils/models.py` | 新增：模型清單唯一定義 |
| `frontend/app_pages/stats.py` | 修改：全部區塊 `@st.fragment(run_every=...)` |
| `frontend/app_pages/chat.py` | 修改：引用 `utils.cache`、`utils.models` |
| `frontend/app_pages/admin.py` | 修改：引用 `utils.cache`、`utils.models`，移除重複模型清單 |

---

## 任務三：程式碼架構重組（依 `organizing-streamlit-code` + `building-streamlit-multipage-apps` skill）

### 3.1 現況問題

| 問題 | 說明 |
|------|------|
| `pages/` 目錄名衝突 | 使用 `pages/` 目錄名觸發 Streamlit 舊版自動探索 API，與 `st.navigation` 行為衝突 |
| 每頁都呼叫 `st.set_page_config` | 應只在 entrypoint 呼叫一次；子頁面重複呼叫會產生警告 |
| 舊頁面命名含 emoji + 序號 | `1_💬_Chat.py` 為舊式自動探索格式；改為 `app_pages/chat.py` 搭配 `st.Page()` |
| 模型清單重複 2 份 | `Chat.py` 和 `Admin.py` 各維護一份 ~30 個模型的 dict list |
| 快取函式分散各頁 | 無法統一管理 TTL 和 max_entries |
| `components/` 缺少 stats 組件 | Stats 圖表邏輯全部寫在頁面內，無法重用 |
| 兩個 App 混用同一入口 | Chat 和 Admin/Stats 在同一 `Home.py` 導覽，Port 分離後需各自 entrypoint |

### 3.2 目標目錄結構

```
frontend/
├── chat_app.py                  # Chat App 入口（Port 8501）
├── admin_app.py                 # Admin+Stats App 入口（Port 8502，含登入驗護）
├── config.py                    # 補充 ADMIN_PORT 設定
├── requirements.txt
│
├── app_pages/                   # ← 更名自 pages/（避免舊 API 衝突）
│   ├── chat.py                  # 對話頁（原 1_💬_Chat.py）
│   ├── admin.py                 # 管理後台（原 2_📁_Admin.py）
│   ├── stats.py                 # 統計儀表板（原 3_📊_Stats.py）
│   └── login.py                 # 登入頁（新增，Admin App 專用）
│
├── client/
│   ├── api_client.py            # 新增 ask_stream() 方法
│   └── __init__.py
│
├── components/
│   ├── chat_ui.py               # 保留（搜尋結果卡片、8D 報告）
│   ├── uploader.py              # 保留（拖曳上傳）
│   ├── login_form.py            # 新增：登入表單組件
│   ├── stats_charts.py          # 新增：Stats 圖表（從 stats.py 提取）
│   └── __init__.py
│
└── utils/
    ├── markdown_renderer.py     # 保留
    ├── cache.py                 # 新增：集中快取函式
    ├── models.py                # 新增：模型清單唯一定義
    ├── auth.py                  # 新增：Admin 登入驗證
    └── __init__.py
```

### 3.3 Chat App Entrypoint（`frontend/chat_app.py`）

```python
import streamlit as st
from utils.cache import get_api_client
from config import API_BASE_URL

st.set_page_config(
    page_title="AI Expert System",
    page_icon=":material/support_agent:",
    layout="wide",
)

st.session_state.setdefault("api_client", get_api_client(API_BASE_URL))
st.session_state.setdefault("messages", [])
# ... 其他全域 defaults

page = st.navigation(
    [st.Page("app_pages/chat.py", title="專家問答", icon=":material/chat:")],
    position="top",
)
page.run()
```

### 3.4 Admin App Entrypoint（`frontend/admin_app.py`）

```python
import streamlit as st
from utils.auth import is_admin_logged_in, admin_logout
from utils.cache import get_api_client
from config import API_BASE_URL

st.set_page_config(
    page_title="AI Expert System — 管理",
    page_icon=":material/admin_panel_settings:",
    layout="wide",
)

st.session_state.setdefault("api_client", get_api_client(API_BASE_URL))
st.session_state.setdefault("admin_logged_in", False)

# 條件式頁面（依 building-streamlit-multipage-apps skill）
if not is_admin_logged_in():
    pages = [st.Page("app_pages/login.py", title="登入", icon=":material/lock:")]
else:
    pages = [
        st.Page("app_pages/admin.py", title="管理後台", icon=":material/folder:"),
        st.Page("app_pages/stats.py", title="統計儀表板", icon=":material/bar_chart:"),
    ]
    with st.sidebar:
        st.caption("管理員已登入")
        if st.button(":material/logout: 登出", use_container_width=True):
            admin_logout()
            st.switch_page("app_pages/login.py")

page = st.navigation(pages, position="sidebar")
page.run()
```

---

## 任務四：Admin + Stats 分離 Port，新增登入頁

### 4.1 架構設計

```
Port 8501 → chat_app.py（公開，BYOK 驗證）
              └── app_pages/chat.py

Port 8502 → admin_app.py（需帳密登入）
              ├── app_pages/login.py    ← 登入前唯一頁
              ├── app_pages/admin.py    ← 登入後
              └── app_pages/stats.py   ← 登入後
```

### 4.2 登入頁（`app_pages/login.py`）

```python
import streamlit as st
from utils.auth import verify_admin_credentials

with st.container(horizontal_alignment="center"):
    with st.container(border=True):
        st.markdown("### :material/lock: 管理員登入")
        with st.form("admin_login_form"):
            username = st.text_input("帳號", placeholder="admin")
            password = st.text_input("密碼", type="password")
            submitted = st.form_submit_button(
                ":material/login: 登入", use_container_width=True
            )
        if submitted:
            if verify_admin_credentials(username, password):
                st.session_state.admin_logged_in = True
                st.rerun()
            else:
                st.error("❌ 帳號或密碼錯誤")
```

### 4.3 驗證工具（`utils/auth.py`）

```python
import os, hashlib, hmac
import streamlit as st

def verify_admin_credentials(username: str, password: str) -> bool:
    expected_user = os.getenv("ADMIN_USERNAME", "admin")
    expected_hash = os.getenv("ADMIN_PASSWORD_HASH", "")
    actual_hash = hashlib.sha256(password.encode()).hexdigest()
    return username == expected_user and hmac.compare_digest(actual_hash, expected_hash)

def is_admin_logged_in() -> bool:
    return st.session_state.get("admin_logged_in", False)

def admin_logout():
    st.session_state.admin_logged_in = False
```

### 4.4 環境變數（`.env` 新增）

```dotenv
# Admin App 認證
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=<sha256 of your password>

# Port 設定
FRONTEND_CHAT_PORT=8501
FRONTEND_ADMIN_PORT=8502
```

> 密碼 hash 生成：`python -c "import hashlib; print(hashlib.sha256('YourPassword'.encode()).hexdigest())"`

### 4.5 啟動腳本更新

#### 新增 `scripts/start_admin.bat`(需使用CRLF格式而非Unix LF格式)

```bat
@echo off
chcp 950 >nul
echo ============================================
echo   AI Expert System - Start Admin App
echo ============================================
cd /d "%~dp0\.."
call ".venv\Scripts\activate.bat"
echo [INFO] Starting Admin+Stats app on port 8502...
streamlit run frontend\admin_app.py --server.port 8502 --server.address 0.0.0.0
pause
```

#### 更新 `Start_all.bat`(需使用CRLF格式而非Unix LF格式)

```bat
@echo off
chcp 950 >nul
echo ============================================
echo   AI Expert System - Start All Services
echo ============================================
echo [1/3] Starting FastAPI backend...
start "AI Expert Backend"  cmd /k "scripts\start_backend.bat"

echo [2/3] Starting Chat frontend (port 8501)...
start "AI Expert Chat"     cmd /k "scripts\start_frontend.bat"

echo [3/3] Starting Admin+Stats frontend (port 8502)...
start "AI Expert Admin"    cmd /k "scripts\start_admin.bat"

echo.
echo   Backend  : http://localhost:8000/docs
echo   Chat     : http://localhost:8501
echo   Admin    : http://localhost:8502
pause >nul
```

---

## 執行順序

```
Phase 1（基礎，其他任務的前提）
├── 建立 app_pages/ 目錄，複製並重命名現有頁面
├── 建立 utils/cache.py + utils/models.py
└── 建立 utils/auth.py + components/login_form.py

Phase 2（可並行執行）
├── 任務一：Chat 對話系統優化
├── 任務二：Stats Fragment 化
└── 任務四：login.py + admin/stats 移植

Phase 3（整合）
├── chat_app.py + admin_app.py entrypoint 建立
├── 更新啟動腳本（start_admin.bat、Start_all.bat）
└── 更新 .env.example + README
```

---

## 預估工作量

| 任務 | 預估時間 | 難度 |
|------|---------|------|
| 任務一：Chat 優化 | 2–3 小時 | 🟡 中（後端需配合 streaming） |
| 任務二：快取強化 | 1–2 小時 | 🟢 低 |
| 任務三：架構重組 | 2–3 小時 | 🟡 中（import 全部更新） |
| 任務四：Port 分離 + 登入 | 1–2 小時 | 🟢 低 |
| **合計** | **6–10 小時** | |

---

## 風險與注意事項

| 風險 | 緩解方式 |
|------|---------|
| Streaming 後端未實作 | Phase 1 先用 generator wrap 降級模擬逐字輸出 |
| `pages/` → `app_pages/` 重命名 | 舊書籤 URL 會 404，在 Chat App 加說明提示 |
| Admin 登入密碼管理 | 預留 `scripts/set_admin_password.py` 工具腳本 |
| Fragment 內誤呼叫 `st.rerun()` | Code review 確保 Stats fragment 自給自足，不觸發全頁 rerun |
| Streamlit ≥ 1.37 依賴 | v3.1 已確認升版，確認 `requirements.txt` 版本一致 |

---

## 驗收標準

- [x] Chat App 回答顯示為 streaming 逐字輸出
- [x] 第一次進入 Chat 有 4 個 suggestion chips
- [x] AI 回答後有 👍/👎 feedback 按鈕
- [x] Stats 頁各區塊每 30/60/300 秒獨立 auto-refresh，不觸發全頁 rerun
- [x] `pages/` 重命名為 `app_pages/`，所有 import 正確
- [x] 模型清單只在 `utils/models.py` 定義一次
- [x] 快取函式集中在 `utils/cache.py`，含 `max_entries`
- [x] `http://localhost:8501` 顯示 Chat App（無 Admin/Stats 頁）
- [x] `http://localhost:8502` 首頁為登入頁，正確帳密後進入 Admin/Stats
- [x] 未登入時直接訪問 Admin/Stats URL → 自動跳回登入頁
- [x] `Start_all.bat` 同時啟動 backend / chat / admin 三個視窗

---

*舊版 v3.1 計畫（已完成）請參考 git history（tag: v3.1-complete）。*
