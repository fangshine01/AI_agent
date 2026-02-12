"""
AI Expert System - Chat Page (專家問答介面)
已套用 UI 優化:
- 建議 1: Tab 組織側邊欄
- 建議 2: 快速操作按鈕
- 建議 3: 卡片式搜尋結果
- 建議 4: 載入動畫與進度
- 建議 5: Mermaid 渲染
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

# 初始化
if "api_client" not in st.session_state:
    st.session_state.api_client = APIClient(base_url=API_BASE_URL)
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_tokens" not in st.session_state:
    st.session_state.session_tokens = 0

client: APIClient = st.session_state.api_client

# ========== 側邊欄 (建議 1: Tab 組織) ==========
with st.sidebar:
    st.title("💬 專家問答設定")

    tab1, tab2, tab3 = st.tabs(["🔑 連線", "🎯 搜尋", "📊 狀態"])

    with tab1:
        st.subheader("API 設定")
        if "user_api_key" not in st.session_state:
            st.session_state.user_api_key = ""
        if "user_base_url" not in st.session_state:
            st.session_state.user_base_url = "http://innoai.cminl.oa/agency/proxy/openai/platform"

        user_api_key = st.text_input(
            "API Key",
            value=st.session_state.user_api_key,
            type="password",
            help="請輸入您的 API Key",
        )
        user_base_url = st.text_input(
            "Base URL",
            value=st.session_state.user_base_url,
            help="API 端點 URL",
        )
        st.session_state.user_api_key = user_api_key
        st.session_state.user_base_url = user_base_url

        if user_api_key:
            st.success("✅ API Key 已設定")
        else:
            st.warning("⚠️ 請輸入 API Key")

        chat_model = st.selectbox(
            "問答模型",
            options=["gpt-4o-mini", "gpt-4o", "gemini-2.0-flash-exp"],
        )

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

    with tab3:
        st.subheader("Session 統計")
        st.metric("本次對話 Token", f"{st.session_state.session_tokens:,}")
        st.metric("對話輪數", len([m for m in st.session_state.messages if m["role"] == "user"]))

        if st.button("🗑️ 清空對話記錄"):
            st.session_state.messages = []
            st.session_state.session_tokens = 0
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

    # 確定實際使用的 query_type
    actual_query_type = st.session_state.get("quick_query_type", query_type) if st.session_state.get("quick_query") else query_type

    # 顯示使用者訊息
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # AI 回應 (建議 4: 進度指示)
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

        # 渲染回應 (建議 5: Mermaid 支援)
        render_markdown_with_mermaid(response_text)

        # 顯示 Token
        tokens_used = usage.get("total_tokens", 0)
        st.caption(f"💡 本次使用: {tokens_used} tokens")

        # 卡片式搜尋結果展示 (建議 3)
        if search_results and not is_direct:
            render_search_results_cards(search_results)

        # 更新 session
        st.session_state.session_tokens += tokens_used
        st.session_state.messages.append({
            "role": "assistant",
            "content": response_text,
            "tokens": tokens_used,
            "doc_data": response_text if is_direct else None,
            "doc_name": search_results[0].get("file_name", "document") if search_results else None,
        })

    st.rerun()

# 底部說明
st.markdown("---")
st.caption("💡 提示：使用快速按鈕可一鍵切換查詢模式 | 模糊搜尋可自動修正錯字")
