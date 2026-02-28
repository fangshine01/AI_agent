"""
系統健康指標 — @st.fragment(run_every=30s)

1.50+ 特性: border=True, Material icons, st.badge
"""

import streamlit as st
from datetime import datetime

from config import API_BASE_URL
from utils.cache import cached_health_check


@st.fragment(run_every="30s")
def render_health_metrics():
    """系統健康 — 每 30 秒自動更新"""
    st.markdown("### :material/health_and_safety: 系統健康")
    st.caption(f"更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    health = cached_health_check(API_BASE_URL)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        backend_ok = health.get("status") == "healthy"
        st.metric(
            ":material/dns: 後端服務",
            "正常" if backend_ok else "離線",
            delta="Running" if backend_ok else "Down",
            delta_color="normal" if backend_ok else "inverse",
            border=True,
        )
    with col2:
        watcher_ok = health.get("watcher_active", False)
        st.metric(
            ":material/visibility: 檔案監控",
            "啟動" if watcher_ok else "停止",
            delta="Active" if watcher_ok else "Inactive",
            delta_color="normal" if watcher_ok else "off",
            border=True,
        )
    with col3:
        db_ok = health.get("database_ok", True)
        st.metric(
            ":material/database: 資料庫",
            "正常" if db_ok else "異常",
            delta="Connected" if db_ok else "Error",
            delta_color="normal" if db_ok else "inverse",
            border=True,
        )
    with col4:
        uptime = health.get("uptime", "N/A")
        st.metric(
            ":material/timer: 系統運行",
            str(uptime),
            border=True,
        )
