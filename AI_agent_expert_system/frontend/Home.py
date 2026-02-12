"""
AI Expert System - Frontend Home
Streamlit 應用入口
"""

import streamlit as st
from frontend.config import API_BASE_URL
from frontend.client.api_client import APIClient

# 頁面設定
st.set_page_config(
    page_title="AI Expert System",
    page_icon="🧠",
    layout="wide",
)

# 初始化 API Client
if "api_client" not in st.session_state:
    st.session_state.api_client = APIClient(base_url=API_BASE_URL)

# 首頁
st.title("🧠 AI Expert System")
st.markdown("### 知識庫問答與自動化文件處理系統 v2.0")
st.markdown("---")

# 系統狀態
client: APIClient = st.session_state.api_client
health = client.health_check()

col1, col2, col3 = st.columns(3)

with col1:
    status = "🟢 正常" if health.get("status") == "healthy" else "🔴 離線"
    st.metric("後端狀態", status)

with col2:
    watcher = "🟢 運行中" if health.get("watcher_running") else "🟡 停止"
    st.metric("檔案監控", watcher)

with col3:
    # 取得統計
    stats = client.get_stats()
    doc_count = stats.get("data", {}).get("documents", {}).get("total_documents", 0)
    st.metric("文件總數", doc_count)

st.markdown("---")

# 導覽
st.markdown("### 📌 功能導覽")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    #### 💬 專家問答
    - 智能搜尋知識庫
    - 多種查詢模式
    - AI 即時回答
    """)

with col2:
    st.markdown("""
    #### 📁 管理後台
    - 拖放上傳檔案
    - 資料庫管理
    - 即時處理進度
    """)

with col3:
    st.markdown("""
    #### 📊 統計儀表板
    - Token 使用趨勢
    - 文件處理統計
    - 系統健康監控
    """)

st.markdown("---")
st.caption("AI Expert System v2.0 | FastAPI Backend + Streamlit Frontend")
