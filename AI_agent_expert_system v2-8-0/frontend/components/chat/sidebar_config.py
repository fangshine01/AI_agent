"""
Chat 側邊欄配置 — 連線 / 搜尋 / 歷史 / 狀態

從 chat.py 拆出，回傳側邊欄中使用者選取的參數。
依 choosing-streamlit-selection-widgets skill：
- st.segmented_control 取代 horizontal st.radio（2-5 項可見選項）
"""

import streamlit as st

from config import API_BASE_URL
from utils.cache import cached_health_check
from utils.models import format_model_display, get_model_id
from components.chat.handlers import (
    verify_and_set_identity,
    clear_chat,
)
from components.chat.session_list import render_session_list


def render_chat_sidebar(client) -> dict:
    """
    渲染 Chat 側邊欄，回傳需要的設定字典：
    {chat_model, query_type, selected_types, search_filters, search_limit, enable_fuzzy}
    """
    with st.sidebar:
        st.title(":blue[:material/chat:] 專家問答設定")

        tab1, tab2, tab3, tab4 = st.tabs([
            ":orange[:material/key:] 連線",
            ":blue[:material/search:] 搜尋",
            ":green[:material/history:] 歷史",
            ":violet[:material/bar_chart:] 狀態",
        ])

        # ---- Tab 1: BYOK 連線設定 ----
        with tab1:
            st.subheader("API 設定")

            with st.form("byok_form", clear_on_submit=False):
                user_api_key = st.text_input(
                    "API Key",
                    value=st.session_state.user_api_key,
                    type="password",
                    help="請輸入您的 API Key（企業 API 同時支援 OpenAI 與 Gemini 模型）",
                )
                user_base_url = st.text_input(
                    "Base URL",
                    value=st.session_state.user_base_url,
                    help="企業 API Proxy 端點 URL",
                )
                user_name = st.text_input(
                    "使用者名稱 (可選)",
                    value=st.session_state.user_name_input,
                    help="用於增加身份唯一性，可留空",
                )
                byok_submitted = st.form_submit_button(
                    ":orange[:material/vpn_key:] 驗證 API Key", width="stretch"
                )

            if byok_submitted:
                st.session_state.user_api_key = user_api_key
                st.session_state.user_base_url = user_base_url
                st.session_state.user_name_input = user_name
                if not user_api_key:
                    st.error("請先輸入 API Key")
                else:
                    verify_and_set_identity(client, user_api_key, user_name, user_base_url)
                    st.rerun()

            if st.session_state.byok_verified:
                st.badge("已驗證", icon=":material/check_circle:", color="green")
                st.caption(f"ID: {st.session_state.byok_user_hash}")
            elif st.session_state.user_api_key:
                st.caption(":orange[:material/key:] 已輸入 Key，請點擊驗證")
            else:
                st.warning("⚠️ 請輸入 API Key 並驗證")

            # 模型選擇
            _models = st.session_state.available_models
            selected_model_obj = st.selectbox(
                "問答模型",
                options=_models,
                format_func=format_model_display,
            )
            chat_model = get_model_id(selected_model_obj)

        # ---- Tab 2: 搜尋設定 ----
        with tab2:
            st.subheader("查詢設定")

            display_options = {
                "general": ":blue[:material/search:] 一般搜尋",
                "troubleshooting": ":red[:material/build:] 異常解析",
                "procedure": ":green[:material/checklist:] SOP 手順",
                "knowledge": ":orange[:material/menu_book:] 技術規格",
                "training": ":violet[:material/school:] 培訓教材",
            }

            query_type = st.segmented_control(
                "查詢情境",
                options=list(display_options.keys()),
                format_func=lambda x: display_options[x],
                default="general",
                key="chat_query_type_seg",
            ) or "general"

            selected_types = []
            if query_type == "general":
                selected_types = st.multiselect(
                    "搜尋範圍",
                    options=["knowledge", "training", "procedure", "troubleshooting"],
                    default=[],
                    format_func=lambda x: {
                        "knowledge": ":orange[:material/menu_book:] 知識庫",
                        "training": ":violet[:material/school:] 教育訓練",
                        "procedure": ":green[:material/checklist:] 日常手順",
                        "troubleshooting": ":red[:material/build:] 異常解析",
                    }[x],
                )
            else:
                selected_types = [query_type]

            search_filters = {}
            if query_type == "troubleshooting":
                with st.form("search_filter_form", clear_on_submit=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        prod = st.text_input(
                            "產品型號", placeholder="e.g. N706",
                            value=st.session_state.get("filter_prod", ""),
                        )
                    with col2:
                        station = st.text_input(
                            "機台/站點", placeholder="e.g. Oven",
                            value=st.session_state.get("filter_station", ""),
                        )
                    filter_submitted = st.form_submit_button(
                        ":blue[:material/search:] 套用過濾", width="stretch"
                    )
                if filter_submitted:
                    st.session_state.filter_prod = prod
                    st.session_state.filter_station = station
                if st.session_state.get("filter_prod"):
                    search_filters["product"] = st.session_state.filter_prod
                if st.session_state.get("filter_station"):
                    search_filters["station"] = st.session_state.filter_station

            search_limit = st.slider("搜尋結果數", 1, 20, 5)
            enable_fuzzy = st.toggle("啟用模糊搜尋", value=True)

        # ---- Tab 3: 對話歷史 (@st.fragment) ----
        with tab3:
            render_session_list(client, chat_model)

        # ---- Tab 4: 狀態 ----
        with tab4:
            st.subheader("Session 統計")
            st.metric(
                "本次對話 Token",
                f"{st.session_state.session_tokens:,}",
                border=True,
            )
            st.metric(
                "對話輪數",
                len([m for m in st.session_state.messages if m["role"] == "user"]),
                border=True,
            )

            if st.session_state.byok_verified:
                st.caption(f":blue[:material/badge:] 身份: {st.session_state.byok_user_hash}")
                if st.session_state.current_session_id:
                    st.caption(f":orange[:material/edit_note:] Session: {st.session_state.current_session_id[:8]}...")

            st.button(
                ":red[:material/delete_sweep:] 清除對話",
                on_click=clear_chat,
                width="stretch",
            )

            health = cached_health_check(API_BASE_URL)
            if health.get("status") == "healthy":
                st.badge("後端正常", icon=":material/check_circle:", color="green")
            else:
                st.badge("後端離線", icon=":material/error:", color="red")

    return {
        "chat_model": chat_model,
        "query_type": query_type,
        "selected_types": selected_types,
        "search_filters": search_filters,
        "search_limit": search_limit,
        "enable_fuzzy": enable_fuzzy,
    }
