"""
AI Expert System - Stats Dashboard (統計儀表板) v4.0.0

架構：slim orchestrator
- components/stats/health_metrics.py — 系統健康 (30s)
- components/stats/doc_overview.py   — 文件概覽 (300s)
- components/stats/token_charts.py   — Token 分析 (60s)
- components/stats/search_analytics.py — 搜尋分析 (60s)
- components/stats/system_resources.py — 系統資源 (300s)

依 .github/skills:
- optimizing-streamlit-performance: @st.fragment(run_every=...) 獨立 auto-refresh
- choosing-streamlit-selection-widgets: st.segmented_control 取代 selectbox (2-5 可見項)
- improving-streamlit-design: Material icons, border=True
"""

import streamlit as st

from utils.cache import (
    cached_health_check,
    cached_get_stats,
    cached_token_stats,
)
from components.stats import (
    render_health_metrics,
    render_doc_overview,
    render_token_charts,
    render_search_analytics,
    render_system_resources,
)


# ========== 側邊欄 ==========
with st.sidebar:
    st.title(":material/bar_chart: 統計設定")

    st.subheader(":material/schedule: 時間範圍")
    date_range = st.segmented_control(
        "選擇區間",
        options=["今日", "近 7 天", "近 30 天", "全部"],
        default="近 7 天",
        key="stats_date_range",
    )

    st.divider()

    if st.button(":material/refresh: 強制刷新全部快取", width="stretch"):
        cached_health_check.clear()
        cached_get_stats.clear()
        cached_token_stats.clear()
        st.rerun()

    st.divider()
    st.caption("各區塊獨立 auto-refresh：")
    st.caption("• 健康: 30s  • Token: 60s  • 文件/資源: 300s")


# ========== 主畫面 ==========
st.title(":material/bar_chart: 系統統計儀表板")

render_health_metrics()
st.divider()
render_doc_overview()
st.divider()
render_token_charts()
st.divider()
render_search_analytics()
st.divider()
render_system_resources()

st.caption(":material/info: 統計儀表板 v4.0 | Fragment auto-refresh + 集中快取 + Plotly 互動圖表")
