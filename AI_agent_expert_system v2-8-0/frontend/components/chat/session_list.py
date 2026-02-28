"""
Session 歷史列表 — @st.fragment 局部更新

從 chat.py 拆出，只在按鈕互動時重繪此 fragment。
"""

import streamlit as st

from components.chat.handlers import (
    new_session,
    refresh_session_list,
    load_session,
    clear_chat,
)


@st.fragment
def render_session_list(client, chat_model: str):
    """Session 歷史列表 — 按鈕操作只重繪此 fragment"""
    st.subheader("對話歷史")

    if not st.session_state.byok_verified:
        st.caption(":orange[:material/key:] 請先驗證 API Key 以存取對話歷史")
        return

    with st.container(horizontal=True):
        if st.button(":green[:material/add:] 新對話", key="new_session_btn"):
            new_session(client, model_used=chat_model)
            st.rerun()
        if st.button(":blue[:material/refresh:] 重新整理", key="refresh_sessions_btn"):
            refresh_session_list(client)

    sessions = st.session_state.session_list
    if not sessions:
        st.caption("尚無對話記錄")
        return

    for idx, s in enumerate(sessions):
        title = s.get("title", "未命名對話")
        msg_count = s.get("message_count", 0)
        is_current = s["session_id"] == st.session_state.current_session_id

        col_load, col_del = st.columns([4, 1])
        with col_load:
            label = f"{'▶ ' if is_current else ''}{title} ({msg_count})"
            if st.button(label, key=f"load_{idx}", width="stretch"):
                load_session(client, s["session_id"])
                st.rerun()
        with col_del:
            if st.button(":red[:material/delete:]", key=f"del_{idx}"):
                client.delete_session(s["session_id"])
                if s["session_id"] == st.session_state.current_session_id:
                    clear_chat()
                refresh_session_list(client)
                st.rerun()
