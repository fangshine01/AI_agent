"""
搜尋分析 — @st.fragment(run_every=60s)

1.50+ 特性: border=True, Material icons, width="stretch"
"""

import streamlit as st
import pandas as pd
import logging

try:
    import plotly.express as px
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

from config import API_BASE_URL
from utils.cache import cached_get_stats

logger = logging.getLogger(__name__)


@st.fragment(run_every="60s")
def render_search_analytics():
    """搜尋分析 — 中頻更新（每 60 秒）"""
    st.markdown("### :material/search: 搜尋分析")

    try:
        stats = cached_get_stats(API_BASE_URL)
        search_analytics = stats.get("search_analytics", {})

        if not search_analytics:
            st.info(":material/mail: 尚無搜尋分析資料")
            return

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                ":material/search: 總搜尋次數",
                search_analytics.get("total_searches", 0),
                border=True,
            )
        with col2:
            st.metric(
                ":material/check_circle: 成功率",
                f"{search_analytics.get('success_rate', 0):.1%}",
                border=True,
            )
        with col3:
            st.metric(
                ":material/timer: 平均耗時",
                f"{search_analytics.get('avg_latency_ms', 0):.0f} ms",
                border=True,
            )

        # 熱門查詢
        top_queries = search_analytics.get("top_queries", [])
        if top_queries:
            st.markdown("#### :material/local_fire_department: 熱門查詢關鍵字")
            df_queries = pd.DataFrame(top_queries)
            if HAS_PLOTLY and "query" in df_queries.columns and "count" in df_queries.columns:
                fig = px.bar(
                    df_queries.head(10),
                    x="count",
                    y="query",
                    orientation="h",
                    color_discrete_sequence=["#F59E0B"],
                )
                fig.update_layout(
                    height=300,
                    margin=dict(l=20, r=20, t=20, b=20),
                    yaxis={"categoryorder": "total ascending"},
                )
                st.plotly_chart(fig, width="stretch")
            else:
                st.dataframe(df_queries, width="stretch")

    except Exception as e:
        st.warning(f"無法載入搜尋分析: {e}")
