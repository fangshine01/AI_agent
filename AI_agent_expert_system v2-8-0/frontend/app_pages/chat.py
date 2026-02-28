"""
AI Expert System - Chat Page (專家問答介面) v4.0.0

架構：slim orchestrator
- components/chat/handlers.py — 業務邏輯
- components/chat/session_list.py — @st.fragment 對話歷史
- components/chat/sidebar_config.py — 側邊欄（4-tab BYOK/搜尋/歷史/狀態）

依 .github/skills:
- building-streamlit-chat-ui: streaming, suggestion chips, feedback, avatars
- optimizing-streamlit-performance: @st.fragment 避免全頁刷新
- organizing-streamlit-code: 主檔 < 200 行
"""

import streamlit as st
import logging

from utils.models import AVAILABLE_MODELS
from utils.markdown_renderer import render_markdown_with_mermaid
from components.chat_ui import render_search_results_cards
from components.chat.handlers import (
    new_session,
    save_message_to_history,
    simulate_stream,
)
from components.chat.sidebar_config import render_chat_sidebar

logger = logging.getLogger(__name__)

# ========== 集中 Session State 初始化 ==========
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
    "available_models": AVAILABLE_MODELS,
}
for _k, _v in _SS_DEFAULTS.items():
    st.session_state.setdefault(_k, _v)

client = st.session_state.api_client

# ========== Suggestion Chips ==========
SUGGESTIONS = {
    ":blue[:material/build:] 查 SOP 步驟": "請列出製程的標準作業步驟",
    ":orange[:material/search:] 查故障排除": "這個錯誤碼代表什麼意思？如何排除？",
    ":green[:material/description:] 查技術文件": "找出相關的技術規範文件",
    ":violet[:material/history:] 查歷史案例": "有沒有類似問題的處理案例？",
}

# ========== 側邊欄（委派） ==========
cfg = render_chat_sidebar(client)
chat_model = cfg["chat_model"]
query_type = cfg["query_type"]
selected_types = cfg["selected_types"]
search_filters = cfg["search_filters"]
search_limit = cfg["search_limit"]
enable_fuzzy = cfg["enable_fuzzy"]

# ========== 主畫面 ==========
st.markdown("### :blue[:material/chat:] 對話記錄")

# ---- Suggestion Chips ----
if not st.session_state.messages:
    selected = st.pills(
        "快速開始：",
        list(SUGGESTIONS.keys()),
        label_visibility="collapsed",
        default=None,
        key="suggestion_pills",
    )
    if selected:
        prompt = SUGGESTIONS[selected]
        del st.session_state["suggestion_pills"]
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()

# ---- 對話記錄（含 avatar + feedback） ----
for index, message in enumerate(st.session_state.messages):
    avatar = ":material/person:" if message["role"] == "user" else ":material/support_agent:"
    with st.chat_message(message["role"], avatar=avatar):
        render_markdown_with_mermaid(message["content"])

        if message["role"] == "assistant":
            if "tokens" in message:
                st.caption(f":green[:material/token:] 本次使用: {message['tokens']} tokens")

            if message.get("doc_data"):
                st.download_button(
                    label=":blue[:material/download:] 下載 (Markdown)",
                    data=message["doc_data"],
                    file_name=f"{message.get('doc_name', 'document')}.md",
                    mime="text/markdown",
                    key=f"dl_{index}",
                )

            # Feedback（僅最後一條 AI 回覆）
            if index == len(st.session_state.messages) - 1:
                feedback = st.feedback("thumbs", key=f"fb_{index}")
                if feedback is not None:
                    st.toast(
                        "感謝您的回饋！" if feedback == 1 else "感謝！我們會繼續改善。",
                        icon="🙏",
                    )

# ---- 使用者輸入 ----
if prompt := st.chat_input("請輸入您的問題..."):
    if not st.session_state.user_api_key:
        st.error(":red[:material/error:] 請先在左側設定 API Key 才能進行對話")
        st.stop()

    if not st.session_state.byok_verified:
        st.error(":red[:material/error:] 請先驗證 API Key（左側「連線」分頁 → 驗證）")
        st.stop()

    if not st.session_state.current_session_id:
        new_session(client, model_used=chat_model)

    actual_query_type = (
        st.session_state.get("quick_query_type", query_type)
        if st.session_state.get("quick_query")
        else query_type
    )

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=":material/person:"):
        st.markdown(prompt)

    save_message_to_history(client, role="user", content=prompt)

    # ---- AI 回應（streaming progress） ----
    with st.chat_message("assistant", avatar=":material/support_agent:"):
        progress_container = st.container()

        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()

            status_text.markdown(":blue[:material/search:] 步驟 1/3: 搜尋知識庫...")
            progress_bar.progress(33)

            result = client.chat(
                query=prompt,
                query_type=actual_query_type,
                chat_model=chat_model,
                search_limit=search_limit,
                selected_types=selected_types,
                filters=search_filters,
                enable_fuzzy=enable_fuzzy,
                api_key=st.session_state.user_api_key,
                base_url=st.session_state.user_base_url,
            )

            status_text.markdown(":orange[:material/edit_note:] 步驟 2/3: 整理參考資料...")
            progress_bar.progress(66)

            status_text.markdown(":green[:material/smart_toy:] 步驟 3/3: AI 生成回答...")
            progress_bar.progress(100)

            progress_container.empty()

        response_text = result.get("response", "抱歉，無法取得回應。")
        search_results = result.get("search_results", [])
        usage = result.get("usage", {})
        search_meta = result.get("search_meta", {})
        is_direct = result.get("is_direct_retrieval", False)

        if search_meta:
            intent = search_meta.get("intent", "")
            strategy = search_meta.get("strategy", "")
            if intent:
                st.info(f":blue[:material/target:] 查詢意圖: **{intent}** | :green[:material/search:] 策略: **{strategy}**")

        response = st.write_stream(simulate_stream(response_text))

        tokens_used = usage.get("total_tokens", 0)
        st.caption(f":green[:material/token:] 本次使用: {tokens_used} tokens")

        if search_results and not is_direct:
            render_search_results_cards(search_results)

        st.session_state.session_tokens += tokens_used
        st.session_state.messages.append({
            "role": "assistant",
            "content": response_text,
            "tokens": tokens_used,
            "doc_data": response_text if is_direct else None,
            "doc_name": search_results[0].get("file_name", "document") if search_results else None,
        })

        save_message_to_history(
            client,
            role="assistant",
            content=response_text,
            model_used=chat_model,
            tokens_used=tokens_used,
        )

    st.rerun()

# ---- 底部說明 ----
st.caption(":orange[:material/lightbulb:] 提示：初次進入可點選上面的建議快速開始 | 模糊搜尋可自動修正錯字")
