"""
Token 統計圖表 — Admin Tab 4

從 admin.py 拆出，負責：
- Token 摘要 metrics
- 每日趨勢、模型/操作分佈、使用者/小時/Top 文件圖表
"""

import streamlit as st
import pandas as pd
import logging

try:
    import plotly.express as px
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

logger = logging.getLogger(__name__)


def render_token_charts(client):
    """渲染 Token 統計 Tab 內容"""
    st.subheader(":material/payments: Token 使用統計")

    try:
        token_data = client.get_token_stats()
        if not token_data:
            st.info(":material/inbox: 尚無 Token 使用紀錄")
            return

        summary = token_data.get("summary", {})

        # KPI 指標 (使用 border=True, 依 building-streamlit-dashboards skill)
        with st.container(horizontal=True):
            st.metric("總 Token", f"{summary.get('total_tokens', 0):,}", border=True)
            st.metric("總請求數", f"{summary.get('total_requests', 0):,}", border=True)
            st.metric("預估費用", f"${summary.get('estimated_cost', 0):.4f}", border=True)
            st.metric("今日 Token", f"{summary.get('today_tokens', 0):,}", border=True)

        if not HAS_PLOTLY:
            st.warning(":material/warning: 請安裝 plotly 以啟用互動圖表: `pip install plotly`")
            daily_data = token_data.get("daily", [])
            if daily_data:
                st.markdown("#### 每日 Token (表格)")
                st.dataframe(pd.DataFrame(daily_data), width="stretch")
            return

        # 每日趨勢
        daily_data = token_data.get("daily", [])
        if daily_data:
            st.markdown("#### :material/trending_up: 每日 Token 趨勢")
            df_daily = pd.DataFrame(daily_data)
            if "date" in df_daily.columns and "tokens" in df_daily.columns:
                fig = px.bar(
                    df_daily, x="date", y="tokens",
                    title="每日 Token 使用量",
                    labels={"date": "日期", "tokens": "Token 數"},
                    color_discrete_sequence=["#4F46E5"],
                )
                fig.update_layout(height=350, margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig, width="stretch")

        # 分佈圖
        by_model = token_data.get("by_model", [])
        by_operation = token_data.get("by_operation", [])

        col1, col2 = st.columns(2)
        with col1:
            if by_model:
                st.markdown("#### :material/smart_toy: 模型使用分佈")
                df_model = pd.DataFrame(by_model)
                if "model" in df_model.columns and "tokens" in df_model.columns:
                    fig = px.pie(df_model, names="model", values="tokens", title="各模型 Token 佔比")
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, width="stretch")
        with col2:
            if by_operation:
                st.markdown("#### :material/bolt: 操作類型分佈")
                df_op = pd.DataFrame(by_operation)
                if "operation" in df_op.columns and "tokens" in df_op.columns:
                    fig = px.pie(df_op, names="operation", values="tokens", title="各操作 Token 佔比")
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, width="stretch")

        # By User Hash
        by_user = token_data.get("by_user", [])
        if by_user:
            st.markdown("#### :material/person: 使用者 Token 統計")
            df_user = pd.DataFrame(by_user)
            if "user_id" in df_user.columns and "tokens" in df_user.columns:
                fig = px.bar(
                    df_user.head(20), x="user_id", y="tokens",
                    title="各使用者 Token 使用量",
                    labels={"user_id": "使用者 (Hash)", "tokens": "Token 數"},
                    color_discrete_sequence=["#F59E0B"],
                )
                fig.update_layout(height=350, margin=dict(l=20, r=20, t=40, b=20), xaxis_tickangle=-45)
                st.plotly_chart(fig, width="stretch")

                with st.expander("使用者明細表格", icon=":material/table_chart:"):
                    st.dataframe(
                        df_user.rename(columns={
                            "user_id": "使用者 Hash",
                            "tokens": "Token",
                            "requests": "請求數",
                        }),
                        width="stretch",
                        hide_index=True,
                    )

        # By Hour
        by_hour = token_data.get("by_hour", [])
        if by_hour:
            st.markdown("#### :material/schedule: 每小時使用量")
            df_hour = pd.DataFrame(by_hour)
            if "hour" in df_hour.columns and "tokens" in df_hour.columns:
                fig = px.bar(
                    df_hour, x="hour", y="tokens",
                    title="24 小時 Token 分佈",
                    labels={"hour": "小時 (0-23)", "tokens": "Token 數"},
                    color_discrete_sequence=["#8B5CF6"],
                )
                fig.update_layout(height=300, margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig, width="stretch")

        # Top 檔案
        top_files = token_data.get("top_files", [])
        if top_files:
            st.markdown("#### :material/folder: Top 10 耗 Token 文件")
            df_files = pd.DataFrame(top_files)
            if "file_name" in df_files.columns and "tokens" in df_files.columns:
                fig = px.bar(
                    df_files.head(10), x="tokens", y="file_name",
                    orientation="h",
                    title="最消耗 Token 的文件",
                    labels={"tokens": "Token 數", "file_name": "檔案名稱"},
                    color_discrete_sequence=["#10B981"],
                )
                fig.update_layout(
                    height=350,
                    margin=dict(l=20, r=20, t=40, b=20),
                    yaxis={"categoryorder": "total ascending"},
                )
                st.plotly_chart(fig, width="stretch")

    except Exception as e:
        st.error(f"❌ 載入 Token 統計失敗: {e}")
