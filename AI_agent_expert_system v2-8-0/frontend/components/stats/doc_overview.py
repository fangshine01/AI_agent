"""
文件概覽統計 — @st.fragment(run_every=300s)

1.50+ 特性: border=True on metrics, Material icons, width="stretch"
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


@st.fragment(run_every="300s")
def render_doc_overview():
    """文件統計 — 低頻更新（每 5 分鐘）"""
    st.markdown("### :material/description: 文件概覽")

    try:
        stats = cached_get_stats(API_BASE_URL)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(
                ":material/article: 文件總數",
                stats.get("total_documents", 0),
                border=True,
            )
        with col2:
            st.metric(
                ":material/inventory_2: 分塊總數",
                stats.get("total_chunks", 0),
                border=True,
            )
        with col3:
            st.metric(
                ":material/key: 關鍵字數",
                stats.get("total_keywords", 0),
                border=True,
            )
        with col4:
            avg_chunks = stats.get("avg_chunks_per_doc", 0)
            st.metric(
                ":material/analytics: 平均分塊",
                f"{avg_chunks:.1f}",
                border=True,
            )

        # 文件類型分佈
        doc_types = stats.get("doc_type_distribution", {})
        if doc_types and HAS_PLOTLY:
            st.markdown("#### :material/folder: 文件類型分佈")
            col1, col2 = st.columns(2)

            df_types = pd.DataFrame([
                {"類型": k, "數量": v} for k, v in doc_types.items()
            ])

            with col1:
                fig = px.pie(
                    df_types,
                    names="類型",
                    values="數量",
                    title="文件類型佔比",
                    color_discrete_sequence=px.colors.qualitative.Set3,
                )
                fig.update_layout(height=300)
                st.plotly_chart(fig, width="stretch")

            with col2:
                fig = px.bar(
                    df_types,
                    x="類型",
                    y="數量",
                    title="各類型文件數量",
                    color="類型",
                    color_discrete_sequence=px.colors.qualitative.Set3,
                )
                fig.update_layout(height=300)
                st.plotly_chart(fig, width="stretch")
        elif doc_types:
            st.dataframe(
                pd.DataFrame([{"類型": k, "數量": v} for k, v in doc_types.items()]),
                width="stretch",
            )
    except Exception as e:
        st.warning(f"無法載入文件統計: {e}")
