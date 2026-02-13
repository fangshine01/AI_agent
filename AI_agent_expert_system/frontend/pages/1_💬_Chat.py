"""
AI Expert System - Chat Page (專家問答介面) v2.3.0

已套用功能:
- BYOK (Bring Your Own Key) 身份驗證
- 對話歷史 (Session 管理 + 持久化)
- UI 優化 (Tab 側邊欄、快速按鈕、卡片式結果、Mermaid)
- 13 模型下拉選擇器 (企業 API Proxy 統一端點)
"""

import streamlit as st
import logging
from frontend.client.api_client import APIClient
from frontend.config import API_BASE_URL
from frontend.utils.markdown_renderer import render_markdown_with_mermaid
from frontend.components.chat_ui import (
    render_search_results_cards,
    render_troubleshooting_metadata,
    render_8d_report,
)

logger = logging.getLogger(__name__)

# 頁面設定
st.set_page_config(page_title="AI Expert System - 專家問答", page_icon="💬", layout="wide")

# 初始化 API Client
if "api_client" not in st.session_state:
    st.session_state.api_client = APIClient(base_url=API_BASE_URL)
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_tokens" not in st.session_state:
    st.session_state.session_tokens = 0
# BYOK 身份驗證狀態
if "byok_verified" not in st.session_state:
    st.session_state.byok_verified = False
if "byok_user_hash" not in st.session_state:
    st.session_state.byok_user_hash = ""
if "available_models" not in st.session_state:
    # 預設模型清單（驗證後會被後端回傳的完整清單覆蓋）
    # 企業 API Proxy 同時支援 OpenAI + Gemini，共 13 個模型
    st.session_state.available_models = [
        {"display_name": "GPT-4.1", "model_id": "gpt-4.1-preview", "category": "Default High-end", "cost_label": "💰💰💰"},
        {"display_name": "GPT-4.1-mini", "model_id": "gpt-4.1-mini-preview", "category": "Default Fast", "cost_label": "💰"},
        {"display_name": "GPT-4o", "model_id": "gpt-4o", "category": "Standard", "cost_label": "💰💰"},
        {"display_name": "GPT-4o-mini", "model_id": "gpt-4o-mini", "category": "Standard Fast", "cost_label": "💰"},
        {"display_name": "gemini-2.5-pro", "model_id": "gemini-2.5-pro", "category": "Google High-end", "cost_label": "💰💰💰"},
        {"display_name": "gemini-2.5-flash", "model_id": "gemini-2.5-flash", "category": "Google Fast", "cost_label": "💰"},
        {"display_name": "gemini-2.5-flash-Lite", "model_id": "gemini-2.5-flash-lite", "category": "Google Lite", "cost_label": "💰"},
        {"display_name": "GPT-5.1", "model_id": "gpt-5.1-preview", "category": "Future", "cost_label": "💰💰💰"},
        {"display_name": "GPT-5-mini", "model_id": "gpt-5-mini-preview", "category": "Future", "cost_label": "💰💰"},
        {"display_name": "gemini 3.0 Pro Preview", "model_id": "gemini-3.0-pro-preview", "category": "Future", "cost_label": "💰💰💰"},
        {"display_name": "gemini 3.0 Pro flash Preview", "model_id": "gemini-3.0-flash-preview", "category": "Future", "cost_label": "💰💰"},
        {"display_name": "gemini 2.5 flash image(nano banana)", "model_id": "gemini-2.5-flash-nano-banana", "category": "Image Optimized", "cost_label": "💰"},
        {"display_name": "gemini 3.0 Pro image Preview(nano banana pro)", "model_id": "gemini-3.0-pro-nano-banana", "category": "Image Optimized", "cost_label": "💰💰"},
    ]
# 對話歷史狀態
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None
if "session_list" not in st.session_state:
    st.session_state.session_list = []

client: APIClient = st.session_state.api_client


# ========== 輔助函式 ==========

def _verify_and_set_identity(api_key: str, username: str, base_url: str):
    """驗證 API Key 並設定 BYOK 身份（企業 API Proxy 統一端點）"""
    with st.spinner("🔐 驗證 API Key 中..."):
        result = client.verify_api_key(
            api_key=api_key,
            username=username,
            base_url=base_url,
        )
    if result.get("status") == "valid":
        client.set_user_identity(api_key=api_key, username=username)
        st.session_state.byok_verified = True
        st.session_state.byok_user_hash = result.get("user_hash", "")
        # 更新可用模型列表（後端回傳帶有 display_name 的結構化清單）
        models = result.get("available_models", [])
        if models:
            # 若後端回傳結構化模型清單，直接使用
            if isinstance(models[0], dict) and "model_id" in models[0]:
                st.session_state.available_models = models
            else:
                # 相容舊格式（純字串列表）
                st.session_state.available_models = [
                    {"display_name": m, "model_id": m, "category": "", "cost_label": "💰"}
                    for m in models
                ]
        st.success(f"✅ 驗證成功！身份: {st.session_state.byok_user_hash}")
        _refresh_session_list()
    else:
        st.session_state.byok_verified = False
        st.error(f"❌ 驗證失敗: {result.get('message', '未知錯誤')}")


def _refresh_session_list():
    """重新載入對話歷史列表"""
    if st.session_state.byok_verified:
        result = client.get_sessions()
        if result.get("success"):
            st.session_state.session_list = result.get("sessions", [])


def _load_session(session_id: str):
    """載入指定 Session 的對話記錄"""
    result = client.get_session_history(session_id)
    if result.get("success"):
        st.session_state.current_session_id = session_id
        st.session_state.messages = [
            {"role": m["role"], "content": m["content"], "tokens": m.get("tokens_used", 0)}
            for m in result.get("messages", [])
        ]
        st.session_state.session_tokens = result.get("total_tokens", 0)


def _new_session(model_used: str = None):
    """建立新對話 Session"""
    result = client.create_session(title="新對話", model_used=model_used)
    if result.get("success"):
        st.session_state.current_session_id = result["session_id"]
        st.session_state.messages = []
        st.session_state.session_tokens = 0
        _refresh_session_list()


def _save_message_to_history(role: str, content: str, model_used: str = None, tokens_used: int = 0):
    """將訊息儲存到後端 (靜默失敗，不阻擋 UI)"""
    if st.session_state.current_session_id and st.session_state.byok_verified:
        try:
            client.save_message(
                session_id=st.session_state.current_session_id,
                role=role,
                content=content,
                model_used=model_used,
                tokens_used=tokens_used,
            )
        except Exception as e:
            logger.warning(f"儲存訊息到歷史失敗 (非致命): {e}")

# ========== 側邊欄 (Tab 組織) ==========
with st.sidebar:
    st.title("💬 專家問答設定")

    tab1, tab2, tab3, tab4 = st.tabs(["🔑 連線", "🎯 搜尋", "📜 歷史", "📊 狀態"])

    # ---- Tab 1: BYOK 連線設定 ----
    with tab1:
        st.subheader("API 設定")

        # 企業 API Proxy 統一端點，不需選擇 provider
        if "user_api_key" not in st.session_state:
            st.session_state.user_api_key = ""
        if "user_base_url" not in st.session_state:
            st.session_state.user_base_url = "http://innoai.cminl.oa/agency/proxy/openai/platform"
        if "user_name_input" not in st.session_state:
            st.session_state.user_name_input = ""

        user_api_key = st.text_input(
            "API Key",
            value=st.session_state.user_api_key,
            type="password",
            help="請輸入您的 API Key（企業 API 同時支援 OpenAI 與 Gemini 模型）",
        )
        st.session_state.user_api_key = user_api_key

        user_base_url = st.text_input(
            "Base URL",
            value=st.session_state.user_base_url,
            help="企業 API Proxy 端點 URL",
        )
        st.session_state.user_base_url = user_base_url

        user_name = st.text_input(
            "使用者名稱 (可選)",
            value=st.session_state.user_name_input,
            help="用於增加身份唯一性，可留空",
        )
        st.session_state.user_name_input = user_name

        # 驗證按鈕
        if st.button("🔐 驗證 API Key", use_container_width=True):
            if not user_api_key:
                st.error("請先輸入 API Key")
            else:
                _verify_and_set_identity(user_api_key, user_name, user_base_url)
                st.rerun()

        # 顯示狀態
        if st.session_state.byok_verified:
            st.success(f"✅ 已驗證 | ID: {st.session_state.byok_user_hash}")
        elif user_api_key:
            st.info("🔑 已輸入 Key，請點擊驗證")
        else:
            st.warning("⚠️ 請輸入 API Key 並驗證")

        # 模型選擇 (使用驗證後的可用模型，顯示名稱+分類)
        _models = st.session_state.available_models

        def _format_model(m):
            """將模型物件格式化為下拉選單顯示文字"""
            if isinstance(m, dict):
                cost = m.get("cost_label", "")
                cat = m.get("category", "")
                name = m.get("display_name", m.get("model_id", ""))
                return f"{cost} {name}  ({cat})" if cat else f"{cost} {name}"
            return str(m)

        selected_model_obj = st.selectbox(
            "問答模型",
            options=_models,
            format_func=_format_model,
        )
        # 從結構化物件中提取 model_id
        if isinstance(selected_model_obj, dict):
            chat_model = selected_model_obj.get("model_id", "gpt-4o-mini")
        else:
            chat_model = str(selected_model_obj)

    with tab2:
        st.subheader("查詢設定")

        display_options = {
            "general": "🔍 一般搜尋",
            "troubleshooting": "🔧 異常解析",
            "procedure": "📋 SOP 手順",
            "knowledge": "📚 技術規格",
            "training": "🎓 培訓教材",
        }

        query_type = st.radio(
            "查詢情境",
            options=list(display_options.keys()),
            format_func=lambda x: display_options[x],
        )

        # 分類過濾
        selected_types = []
        if query_type == "general":
            selected_types = st.multiselect(
                "搜尋範圍",
                options=["knowledge", "training", "procedure", "troubleshooting"],
                default=[],
                format_func=lambda x: {
                    "knowledge": "📚 知識庫",
                    "training": "🎓 教育訓練",
                    "procedure": "📋 日常手順",
                    "troubleshooting": "🔧 異常解析",
                }[x],
            )
        elif query_type == "troubleshooting":
            selected_types = ["troubleshooting"]
        elif query_type == "procedure":
            selected_types = ["procedure"]
        elif query_type == "knowledge":
            selected_types = ["knowledge"]
        elif query_type == "training":
            selected_types = ["training"]

        # 動態過濾條件
        search_filters = {}
        if query_type == "troubleshooting":
            col1, col2 = st.columns(2)
            with col1:
                prod = st.text_input("產品型號", placeholder="e.g. N706")
                if prod:
                    search_filters["product"] = prod
            with col2:
                station = st.text_input("機台/站點", placeholder="e.g. Oven")
                if station:
                    search_filters["station"] = station

        search_limit = st.slider("搜尋結果數", 1, 20, 5)
        enable_fuzzy = st.checkbox("啟用模糊搜尋", value=True)

    # ---- Tab 3: 對話歷史 (v2.2.0 新增) ----
    with tab3:
        st.subheader("對話歷史")

        if not st.session_state.byok_verified:
            st.info("🔑 請先驗證 API Key 以存取對話歷史")
        else:
            # 新建對話按鈕
            if st.button("➕ 新對話", use_container_width=True, key="new_session_btn"):
                _new_session(model_used=chat_model)
                st.rerun()

            # 重新整理按鈕
            if st.button("🔄 重新整理", use_container_width=True, key="refresh_sessions_btn"):
                _refresh_session_list()
                st.rerun()

            st.markdown("---")

            # Session 列表
            sessions = st.session_state.session_list
            if not sessions:
                st.caption("尚無對話記錄")
            else:
                for idx, s in enumerate(sessions):
                    title = s.get("title", "未命名對話")
                    msg_count = s.get("message_count", 0)
                    is_current = (s["session_id"] == st.session_state.current_session_id)

                    col_load, col_del = st.columns([4, 1])
                    with col_load:
                        label = f"{'▶ ' if is_current else ''}{title} ({msg_count})"
                        if st.button(label, key=f"load_{idx}", use_container_width=True):
                            _load_session(s["session_id"])
                            st.rerun()
                    with col_del:
                        if st.button("🗑", key=f"del_{idx}"):
                            client.delete_session(s["session_id"])
                            if s["session_id"] == st.session_state.current_session_id:
                                st.session_state.current_session_id = None
                                st.session_state.messages = []
                                st.session_state.session_tokens = 0
                            _refresh_session_list()
                            st.rerun()

    # ---- Tab 4: 狀態 ----
    with tab4:
        st.subheader("Session 統計")
        st.metric("本次對話 Token", f"{st.session_state.session_tokens:,}")
        st.metric("對話輪數", len([m for m in st.session_state.messages if m["role"] == "user"]))

        if st.session_state.byok_verified:
            st.caption(f"🆔 身份: {st.session_state.byok_user_hash}")
            if st.session_state.current_session_id:
                st.caption(f"📝 Session: {st.session_state.current_session_id[:8]}...")

        if st.button("🗑️ 清空當前對話"):
            st.session_state.messages = []
            st.session_state.session_tokens = 0
            st.session_state.current_session_id = None
            st.rerun()

        # 後端狀態
        st.markdown("---")
        health = client.health_check()
        backend_status = "🟢 正常" if health.get("status") == "healthy" else "🔴 離線"
        st.caption(f"後端: {backend_status}")

# ========== 主畫面 ==========
st.title("💬 AI Expert System - 專家問答")
st.caption("由 v2.0 通用查詢引擎驅動 🚀")

# ========== 快速操作按鈕 (建議 2) ==========
st.markdown("### 💬 開始對話")

col1, col2, col3, col4 = st.columns(4)
with col1:
    if st.button("🔧 異常查詢", use_container_width=True):
        st.session_state.quick_query_type = "troubleshooting"
        st.session_state.quick_query = True
with col2:
    if st.button("📋 SOP 查詢", use_container_width=True):
        st.session_state.quick_query_type = "procedure"
        st.session_state.quick_query = True
with col3:
    if st.button("📚 知識查詢", use_container_width=True):
        st.session_state.quick_query_type = "knowledge"
        st.session_state.quick_query = True
with col4:
    if st.button("🎓 教材查詢", use_container_width=True):
        st.session_state.quick_query_type = "training"
        st.session_state.quick_query = True

if st.session_state.get("quick_query"):
    qtype = st.session_state.get("quick_query_type", "general")
    st.info(f"🎯 當前模式: {display_options.get(qtype, qtype)}")
    if st.button("✖️ 取消快速模式"):
        st.session_state.quick_query = False
        st.rerun()

# ========== 對話記錄 ==========
st.markdown("### 對話記錄")

for index, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        # 使用 Mermaid 渲染 (建議 5)
        render_markdown_with_mermaid(message["content"])

        if message["role"] == "assistant":
            if "tokens" in message:
                st.caption(f"💡 本次使用: {message['tokens']} tokens")

            # 下載按鈕
            if message.get("doc_data"):
                st.download_button(
                    label=f"📥 下載 (Markdown)",
                    data=message["doc_data"],
                    file_name=f"{message.get('doc_name', 'document')}.md",
                    mime="text/markdown",
                    key=f"dl_{index}",
                )

# ========== 使用者輸入 ==========
if prompt := st.chat_input("請輸入您的問題..."):
    if not user_api_key:
        st.error("❌ 請先在左側設定 API Key 才能進行對話")
        st.stop()

    if not st.session_state.byok_verified:
        st.error("❌ 請先驗證 API Key（左側「連線」分頁 → 驗證）")
        st.stop()

    # 自動建立 Session (若尚未建立)
    if not st.session_state.current_session_id:
        _new_session(model_used=chat_model)

    # 確定實際使用的 query_type
    actual_query_type = st.session_state.get("quick_query_type", query_type) if st.session_state.get("quick_query") else query_type

    # 顯示使用者訊息
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 儲存使用者訊息到歷史
    _save_message_to_history(role="user", content=prompt)

    # AI 回應 (進度指示)
    with st.chat_message("assistant"):
        progress_container = st.container()

        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()

            # 階段 1: 搜尋
            status_text.text("🔍 步驟 1/3: 搜尋知識庫...")
            progress_bar.progress(33)

            # 呼叫 API
            result = client.chat(
                query=prompt,
                query_type=actual_query_type,
                chat_model=chat_model,
                search_limit=search_limit,
                selected_types=selected_types,
                filters=search_filters,
                enable_fuzzy=enable_fuzzy,
                api_key=user_api_key,
                base_url=user_base_url,
            )

            # 階段 2: 整理
            status_text.text("📝 步驟 2/3: 整理參考資料...")
            progress_bar.progress(66)

            # 階段 3: 完成
            status_text.text("🤖 步驟 3/3: AI 生成回答...")
            progress_bar.progress(100)

            # 清除進度指示
            progress_container.empty()

        # 顯示回應
        response_text = result.get("response", "抱歉，無法取得回應。")
        search_results = result.get("search_results", [])
        usage = result.get("usage", {})
        search_meta = result.get("search_meta", {})
        is_direct = result.get("is_direct_retrieval", False)

        # 顯示查詢元資訊
        if search_meta:
            intent = search_meta.get("intent", "")
            strategy = search_meta.get("strategy", "")
            if intent:
                st.info(f"🎯 查詢意圖: **{intent}** | 🔍 策略: **{strategy}**")

        # 渲染回應 (Mermaid 支援)
        render_markdown_with_mermaid(response_text)

        # 顯示 Token
        tokens_used = usage.get("total_tokens", 0)
        st.caption(f"💡 本次使用: {tokens_used} tokens")

        # 卡片式搜尋結果展示
        if search_results and not is_direct:
            render_search_results_cards(search_results)

        # 更新 session state
        st.session_state.session_tokens += tokens_used
        st.session_state.messages.append({
            "role": "assistant",
            "content": response_text,
            "tokens": tokens_used,
            "doc_data": response_text if is_direct else None,
            "doc_name": search_results[0].get("file_name", "document") if search_results else None,
        })

        # 儲存 AI 回應到歷史
        _save_message_to_history(
            role="assistant",
            content=response_text,
            model_used=chat_model,
            tokens_used=tokens_used,
        )

    st.rerun()

# 底部說明
st.markdown("---")
st.caption("💡 提示：使用快速按鈕可一鍵切換查詢模式 | 模糊搜尋可自動修正錯字")
