"""
AI Expert System - Frontend Home (Combined Entrypoint) v4.1.0

依 building-streamlit-multipage-apps skill：
- st.navigation + st.Page 取代舊 pages/ 自動探索
- st.set_page_config 只在 entrypoint 呼叫一次
- 條件式導覽、Material icons、1.50+ API
"""

import streamlit as st
from config import API_BASE_URL
from client.api_client import APIClient

# 頁面設定（全域唯一）
st.set_page_config(
    page_title="AI Expert System",
    page_icon=":material/psychology:",
    layout="wide",
)

# 全域初始化
st.session_state.setdefault("api_client", APIClient(base_url=API_BASE_URL))

# st.navigation — 所有頁面由 app_pages/ 提供
page = st.navigation(
    {
        "": [
            st.Page("app_pages/chat.py", title="專家問答", icon=":material/chat:", default=True),
        ],
        "管理": [
            st.Page("app_pages/admin.py", title="管理後台", icon=":material/folder:"),
            st.Page("app_pages/stats.py", title="統計儀表板", icon=":material/bar_chart:"),
        ],
    },
    position="sidebar",
)

st.logo("", icon_image=":material/psychology:")

page.run()
