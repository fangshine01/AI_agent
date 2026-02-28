"""
AI Expert System - Admin App Entrypoint
Port 8502：Admin + Stats 入口（需帳密登入）

依 building-streamlit-multipage-apps skill：
- 條件式 st.navigation：未登入 → 登入頁；已登入 → Admin/Stats
- st.set_page_config 只在 entrypoint 呼叫一次
"""

import streamlit as st
from utils.auth import is_admin_logged_in, admin_logout
from utils.cache import get_api_client
from config import API_BASE_URL

st.set_page_config(
    page_title="AI Expert System — 管理",
    page_icon=":material/admin_panel_settings:",
    layout="wide",
)

# 全域初始化
st.session_state.setdefault("api_client", get_api_client(API_BASE_URL))
st.session_state.setdefault("admin_logged_in", False)

# 條件式頁面（依 building-streamlit-multipage-apps skill）
if not is_admin_logged_in():
    pages = [
        st.Page("app_pages/login.py", title="登入", icon=":material/lock:"),
    ]
else:
    pages = [
        st.Page("app_pages/admin.py", title="管理後台", icon=":material/folder:", default=True),
        st.Page("app_pages/stats.py", title="統計儀表板", icon=":material/bar_chart:"),
    ]
    with st.sidebar:
        st.caption("管理員已登入")
        if st.button(":material/logout: 登出", width="stretch"):
            admin_logout()
            st.rerun()

page = st.navigation(pages, position="sidebar")
page.run()
