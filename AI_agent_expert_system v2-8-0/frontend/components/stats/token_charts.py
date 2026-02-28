"""
Token 使用分析 — @st.fragment(run_every=60s)

1.50+ 特性: border=True, Material icons, width="stretch"
"""

import streamlit as st
import pandas as pd
import logging

try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

from config import API_BASE_URL
from utils.cache import cached_token_stats

logger = logging.getLogger(__name__)


@st.fragment(run_every="60s")
def render_token_charts():
    """Token 使用分析 — 中頻更新（每 60 秒）"""
    st.markdown("### :material/payments: Token 使用分析")

    try:
        token_data = cached_token_stats(API_BASE_URL)

        if not token_data:
            st.info(":material/mail: 尚無 Token 使用紀錄")
            return

        summary = token_data.get("summary", {})

        # KPI 指標
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(
                ":material/trending_up: 總 Token",
                f"{summary.get('total_tokens', 0):,}",
                border=True,
            )
        with col2:
            st.metric(
                ":material/analytics: 總請求數",
                f"{summary.get('total_requests', 0):,}",
                border=True,
            )
        with col3:
            st.metric(
                ":material/attach_money: 預估費用",
                f"${summary.get('estimated_cost', 0):.4f}",
                border=True,
            )
        with col4:
            avg_per_req = summary.get("avg_tokens_per_request", 0)
            st.metric(
                ":material/straighten: 平均 Token/請求",
                f"{avg_per_req:,.0f}",
                border=True,
            )

        if not HAS_PLOTLY:
            st.warning(":material/inventory_2: 請安裝 plotly 以啟用互動圖表: `pip install plotly`")
            return

        # 每日趨勢
        daily_data = token_data.get("daily", [])
        if daily_data:
            st.markdown("#### :material/trending_up: Token 使用趨勢")
            df_daily = pd.DataFrame(daily_data)

            if "date" in df_daily.columns and "tokens" in df_daily.columns:
                fig = make_subplots(
                    rows=1, cols=1,
                    specs=[[{"secondary_y": True}]],
                )
                fig.add_trace(
                    go.Bar(
                        x=df_daily["date"],
                        y=df_daily["tokens"],
                        name="Token 使用量",
                        marker_color="#4F46E5",
                    ),
                    secondary_y=False,
                )
                if "requests" in df_daily.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=df_daily["date"],
                            y=df_daily["requests"],
                            name="請求數",
                            mode="lines+markers",
                            marker_color="#EF4444",
                        ),
                        secondary_y=True,
                    )
                fig.update_layout(
                    title="每日 Token 使用量與請求數",
                    height=400,
                    margin=dict(l=20, r=20, t=40, b=20),
                )
                fig.update_yaxes(title_text="Token 數", secondary_y=False)
                fig.update_yaxes(title_text="請求數", secondary_y=True)
                st.plotly_chart(fig, width="stretch")

        # 模型 & 操作分佈
        by_model = token_data.get("by_model", [])
        by_operation = token_data.get("by_operation", [])

        if by_model or by_operation:
            col1, col2 = st.columns(2)

            with col1:
                if by_model:
                    st.markdown("#### :material/smart_toy: 模型分佈")
                    df_model = pd.DataFrame(by_model)
                    if "model" in df_model.columns and "tokens" in df_model.columns:
                        fig = px.pie(
                            df_model,
                            names="model",
                            values="tokens",
                            color_discrete_sequence=px.colors.qualitative.Pastel,
                        )
                        fig.update_layout(height=300)
                        st.plotly_chart(fig, width="stretch")

            with col2:
                if by_operation:
                    st.markdown("#### :material/bolt: 操作分佈")
                    df_op = pd.DataFrame(by_operation)
                    if "operation" in df_op.columns and "tokens" in df_op.columns:
                        fig = px.pie(
                            df_op,
                            names="operation",
                            values="tokens",
                            color_discrete_sequence=px.colors.qualitative.Vivid,
                        )
                        fig.update_layout(height=300)
                        st.plotly_chart(fig, width="stretch")

        # Top 文件
        top_files = token_data.get("top_files", [])
        if top_files:
            st.markdown("#### :material/folder: Top 10 耗 Token 文件")
            df_files = pd.DataFrame(top_files)
            if "file_name" in df_files.columns and "tokens" in df_files.columns:
                fig = px.bar(
                    df_files.head(10),
                    x="tokens",
                    y="file_name",
                    orientation="h",
                    color_discrete_sequence=["#10B981"],
                )
                fig.update_layout(
                    height=350,
                    margin=dict(l=20, r=20, t=20, b=20),
                    yaxis={"categoryorder": "total ascending"},
                )
                st.plotly_chart(fig, width="stretch")

    except Exception as e:
        st.warning(f"無法載入 Token 統計: {e}")
