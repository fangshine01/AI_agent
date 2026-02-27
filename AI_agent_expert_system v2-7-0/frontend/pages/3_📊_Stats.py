"""
AI Expert System - Stats Dashboard (統計儀表板)
提供系統運行狀況的整體視圖, 包含:
- Plotly 互動圖表
- 系統健康指標
- 搜尋分析
"""

import streamlit as st
import pandas as pd
import logging
from datetime import datetime

try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

from client.api_client import APIClient
from config import API_BASE_URL

logger = logging.getLogger(__name__)

# 頁面設定
st.set_page_config(page_title="AI Expert System - 統計", page_icon="📊", layout="wide")

# 初始化
if "api_client" not in st.session_state:
    st.session_state.api_client = APIClient(base_url=API_BASE_URL)

client: APIClient = st.session_state.api_client

# ========== 側邊欄 ==========
with st.sidebar:
    st.title("📊 統計設定")
    st.markdown("---")

    auto_refresh = st.checkbox("🔄 自動更新", value=False)
    if auto_refresh:
        refresh_interval = st.slider("更新間隔 (秒)", 5, 60, 30)
        st.caption(f"每 {refresh_interval} 秒更新一次")

    if st.button("🔄 立即更新", use_container_width=True):
        st.rerun()

    st.markdown("---")
    st.subheader("📆 時間範圍")
    date_range = st.selectbox(
        "選擇區間",
        options=["今日", "近 7 天", "近 30 天", "全部"],
        index=1,
    )

# ========== 主畫面 ==========
st.title("📊 系統統計儀表板")
st.caption(f"更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ========== 系統健康 ==========
st.markdown("### 🏥 系統健康")

health = client.health_check()
col1, col2, col3, col4 = st.columns(4)

with col1:
    backend_ok = health.get("status") == "healthy"
    st.metric(
        "後端服務",
        "🟢 正常" if backend_ok else "🔴 離線",
        delta="Running" if backend_ok else "Down",
        delta_color="normal" if backend_ok else "inverse",
    )
with col2:
    watcher_ok = health.get("watcher_active", False)
    st.metric(
        "檔案監控",
        "🟢 啟動" if watcher_ok else "🟡 停止",
        delta="Active" if watcher_ok else "Inactive",
        delta_color="normal" if watcher_ok else "off",
    )
with col3:
    db_ok = health.get("database_ok", True)
    st.metric(
        "資料庫",
        "🟢 正常" if db_ok else "🔴 異常",
        delta="Connected" if db_ok else "Error",
        delta_color="normal" if db_ok else "inverse",
    )
with col4:
    uptime = health.get("uptime", "N/A")
    st.metric("系統運行", str(uptime))

st.markdown("---")

# ========== 文件統計 ==========
st.markdown("### 📄 文件概覽")

try:
    stats = client.get_stats()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📄 文件總數", stats.get("total_documents", 0))
    with col2:
        st.metric("📦 分塊總數", stats.get("total_chunks", 0))
    with col3:
        st.metric("🔑 關鍵字數", stats.get("total_keywords", 0))
    with col4:
        avg_chunks = stats.get("avg_chunks_per_doc", 0)
        st.metric("📊 平均分塊", f"{avg_chunks:.1f}")

    # 文件類型分佈
    doc_types = stats.get("doc_type_distribution", {})
    if doc_types and HAS_PLOTLY:
        st.markdown("#### 📁 文件類型分佈")
        col1, col2 = st.columns(2)

        with col1:
            df_types = pd.DataFrame([
                {"類型": k, "數量": v} for k, v in doc_types.items()
            ])
            fig = px.pie(
                df_types,
                names="類型",
                values="數量",
                title="文件類型佔比",
                color_discrete_sequence=px.colors.qualitative.Set3,
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

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
            st.plotly_chart(fig, use_container_width=True)
    elif doc_types:
        st.dataframe(
            pd.DataFrame([{"類型": k, "數量": v} for k, v in doc_types.items()]),
            use_container_width=True,
        )
except Exception as e:
    st.warning(f"無法載入文件統計: {e}")

st.markdown("---")

# ========== Token 統計 ==========
st.markdown("### 💰 Token 使用分析")

try:
    token_data = client.get_token_stats()

    if token_data:
        summary = token_data.get("summary", {})

        # 重要指標
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📈 總 Token", f"{summary.get('total_tokens', 0):,}")
        with col2:
            st.metric("📊 總請求數", f"{summary.get('total_requests', 0):,}")
        with col3:
            st.metric("💵 預估總費用", f"${summary.get('estimated_cost', 0):.4f}")
        with col4:
            avg_per_req = summary.get("avg_tokens_per_request", 0)
            st.metric("📏 平均 Token/請求", f"{avg_per_req:,.0f}")

        if HAS_PLOTLY:
            # 每日趨勢
            daily_data = token_data.get("daily", [])
            if daily_data:
                st.markdown("#### 📈 Token 使用趨勢")
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

                    st.plotly_chart(fig, use_container_width=True)

            # 模型 & 操作分佈
            by_model = token_data.get("by_model", [])
            by_operation = token_data.get("by_operation", [])

            if by_model or by_operation:
                col1, col2 = st.columns(2)

                with col1:
                    if by_model:
                        st.markdown("#### 🤖 模型分佈")
                        df_model = pd.DataFrame(by_model)
                        if "model" in df_model.columns and "tokens" in df_model.columns:
                            fig = px.pie(
                                df_model,
                                names="model",
                                values="tokens",
                                color_discrete_sequence=px.colors.qualitative.Pastel,
                            )
                            fig.update_layout(height=300)
                            st.plotly_chart(fig, use_container_width=True)

                with col2:
                    if by_operation:
                        st.markdown("#### ⚡ 操作分佈")
                        df_op = pd.DataFrame(by_operation)
                        if "operation" in df_op.columns and "tokens" in df_op.columns:
                            fig = px.pie(
                                df_op,
                                names="operation",
                                values="tokens",
                                color_discrete_sequence=px.colors.qualitative.Vivid,
                            )
                            fig.update_layout(height=300)
                            st.plotly_chart(fig, use_container_width=True)

            # Top 文件
            top_files = token_data.get("top_files", [])
            if top_files:
                st.markdown("#### 📁 Top 10 耗 Token 文件")
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
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("📦 請安裝 plotly 以啟用互動圖表: `pip install plotly`")
    else:
        st.info("📭 尚無 Token 使用紀錄")
except Exception as e:
    st.warning(f"無法載入 Token 統計: {e}")

st.markdown("---")

# ========== 搜尋分析 ==========
st.markdown("### 🔍 搜尋分析")

try:
    stats = client.get_stats()
    search_analytics = stats.get("search_analytics", {})

    if search_analytics:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🔍 總搜尋次數", search_analytics.get("total_searches", 0))
        with col2:
            st.metric("✅ 成功率", f"{search_analytics.get('success_rate', 0):.1%}")
        with col3:
            st.metric("⏱️ 平均耗時", f"{search_analytics.get('avg_latency_ms', 0):.0f} ms")

        # 熱門查詢
        top_queries = search_analytics.get("top_queries", [])
        if top_queries:
            st.markdown("#### 🔥 熱門查詢關鍵字")
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
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.dataframe(df_queries, use_container_width=True)
    else:
        st.info("📭 尚無搜尋分析資料")
except Exception as e:
    st.warning(f"無法載入搜尋分析: {e}")

# ========== 系統資源 ==========
st.markdown("---")
st.markdown("### 🖥️ 系統資源")

try:
    import os

    col1, col2, col3 = st.columns(3)
    with col1:
        # 資料庫大小（使用 backend 正確路徑）
        import pathlib
        _project_root = pathlib.Path(__file__).resolve().parent.parent.parent
        db_path = str(_project_root / "backend" / "data" / "documents" / "knowledge_v2.db")
        if os.path.exists(db_path):
            db_size = os.path.getsize(db_path) / (1024 * 1024)
            st.metric("💾 知識庫大小", f"{db_size:.1f} MB")
        else:
            st.metric("💾 知識庫大小", "N/A")
    with col2:
        # 檔案數量（使用 backend 正確路徑）
        raw_dir = str(_project_root / "backend" / "data" / "raw_files")
        if os.path.exists(raw_dir):
            file_count = len([f for f in os.listdir(raw_dir) if os.path.isfile(os.path.join(raw_dir, f))])
            st.metric("📂 待處理檔案", file_count)
        else:
            st.metric("📂 待處理檔案", 0)
    with col3:
        archived_dir = str(_project_root / "backend" / "data" / "archived_files")
        if os.path.exists(archived_dir):
            archived_count = len([f for f in os.listdir(archived_dir) if os.path.isfile(os.path.join(archived_dir, f))])
            st.metric("📦 已歸檔檔案", archived_count)
        else:
            st.metric("📦 已歸檔檔案", 0)
except Exception as e:
    st.warning(f"無法載入系統資源: {e}")

# 底部
st.markdown("---")
st.caption("📊 統計儀表板 v2.0 | 支援互動式 Plotly 圖表")

# 自動更新
if auto_refresh:
    import time
    time.sleep(refresh_interval)
    st.rerun()
