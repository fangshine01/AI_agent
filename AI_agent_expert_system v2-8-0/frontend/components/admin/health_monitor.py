"""
系統健康監控 — Admin Tab 5

從 admin.py 拆出，負責：
- 整體健康狀態
- 版本 / 運行時間 / 磁碟
- 資料庫 / 目錄 / Session 細節
"""

import streamlit as st
import logging

logger = logging.getLogger(__name__)


def render_health_tab(client):
    """渲染系統健康 Tab 內容"""
    st.subheader(":material/health_and_safety: 系統健康監控")

    try:
        detailed = client._request("GET", "/health/detailed")

        overall_status = detailed.get("status", "unknown")
        if overall_status == "healthy":
            st.success("系統整體健康", icon=":material/check_circle:")
        elif overall_status == "degraded":
            st.warning("系統部分降級", icon=":material/warning:")
        else:
            st.error("系統異常", icon=":material/error:")

        # KPI 指標
        with st.container(horizontal=True):
            st.metric("版本", detailed.get("version", "N/A"), border=True)
            uptime = detailed.get("uptime_seconds", 0)
            hours = int(uptime // 3600)
            mins = int((uptime % 3600) // 60)
            st.metric("運行時間", f"{hours}h {mins}m", border=True)
            st.metric("磁碟空間", f"{detailed.get('disk_free_gb', '?')} GB", border=True)

        # 資料庫狀態
        dbs = detailed.get("databases", {})
        if dbs:
            st.markdown("#### :material/database: 資料庫狀態")
            for db_name, db_info in dbs.items():
                ok = db_info.get("ok", False)
                icon = ":material/check_circle:" if ok else ":material/error:"
                wal = "WAL" if db_info.get("wal_mode") else "非 WAL"
                latency = db_info.get("latency_ms", "?")
                size = db_info.get("size_mb", "?")
                st.markdown(f"{icon} **{db_name}** | {wal} | 延遲: {latency}ms | 大小: {size} MB")

        # 目錄狀態
        dirs = detailed.get("directories", {})
        if dirs:
            st.markdown("#### :material/folder: 目錄狀態")
            for dir_name, dir_info in dirs.items():
                exists = dir_info.get("exists", False)
                icon = ":material/check:" if exists else ":material/close:"
                count = dir_info.get("file_count", "?")
                st.markdown(f"{icon} **{dir_name}** | 檔案數: {count}")

        # 活躍 Session
        sessions = detailed.get("active_sessions", {})
        if sessions:
            st.markdown("#### :material/group: 活躍連線")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("活躍 Session", sessions.get("count", 0))
            with col2:
                st.metric("不重複使用者", sessions.get("unique_users", 0))

    except Exception as e:
        st.error(f"❌ 無法載入健康資訊: {e}")
        st.caption("請確認後端服務已啟動且 /health/detailed 端點可用")
