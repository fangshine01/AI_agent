"""
AI Expert System - Chat App Entrypoint
Port 8501：Chat 專用入口（公開，BYOK 驗證）

依 building-streamlit-multipage-apps skill：
- st.set_page_config 只在 entrypoint 呼叫一次
- 使用 st.navigation + st.Page 取代舊 pages/ 自動探索
"""

import streamlit as st
from utils.cache import get_api_client
from config import API_BASE_URL

st.set_page_config(
    page_title="AI Expert System",
    page_icon=":material/support_agent:",
    layout="wide",
)

# 全域初始化（所有頁面共用）
st.session_state.setdefault("api_client", get_api_client(API_BASE_URL))
st.session_state.setdefault("messages", [])

page = st.navigation(
    [st.Page("app_pages/chat.py", title="專家問答", icon=":material/chat:")],
    position="hidden",
)
page.run()
