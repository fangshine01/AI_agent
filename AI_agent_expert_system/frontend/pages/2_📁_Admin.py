"""
AI Expert System - Admin Page (管理介面)
已套用 UI 優化:
- 建議 6: 拖拽上傳區
- 建議 7: 實時處理進度
- 建議 8: 批次操作列表
- 建議 9: Token 互動式圖表
"""

import streamlit as st
import pandas as pd
import logging

try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

from frontend.client.api_client import APIClient
from frontend.config import API_BASE_URL
from frontend.components.uploader import render_file_uploader

logger = logging.getLogger(__name__)

# 頁面設定
st.set_page_config(page_title="AI Expert System - 管理後台", page_icon="📁", layout="wide")

# 初始化
if "api_client" not in st.session_state:
    st.session_state.api_client = APIClient(base_url=API_BASE_URL)

client: APIClient = st.session_state.api_client

# ========== 側邊欄 ==========
with st.sidebar:
    st.title("📁 管理設定")

    # API 設定（讓每位使用者輸入自己的 API Key）
    st.subheader("🔑 API 設定")
    if "admin_api_key" not in st.session_state:
        st.session_state.admin_api_key = ""
    if "admin_base_url" not in st.session_state:
        st.session_state.admin_base_url = "http://innoai.cminl.oa/agency/proxy/openai/platform"

    admin_api_key = st.text_input(
        "API Key",
        value=st.session_state.admin_api_key,
        type="password",
        help="上傳檔案處理時使用您的 API Key（入庫需要 Embedding）",
        key="admin_api_key_input",
    )
    admin_base_url = st.text_input(
        "Base URL",
        value=st.session_state.admin_base_url,
        help="API 端點 URL",
        key="admin_base_url_input",
    )
    st.session_state.admin_api_key = admin_api_key
    st.session_state.admin_base_url = admin_base_url

    if admin_api_key:
        st.success("✅ API Key 已設定（上傳將使用您的 Key 處理）")
    else:
        st.warning("⚠️ 未設定 API Key，上傳檔案將由系統排程處理")

    st.markdown("---")

    # 後端健康
    health = client.health_check()
    if health.get("status") == "healthy":
        st.success("🟢 後端連線正常")
    else:
        st.error("🔴 後端離線")

    # 快速操作
    st.subheader("🔧 快速操作")
    if st.button("🔄 重新載入資料", use_container_width=True):
        st.rerun()

# ========== 主畫面 ==========
st.title("📁 管理後台")

# 頂部指標摘要
try:
    stats = client.get_stats()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📄 文件總數", stats.get("total_documents", 0))
    with col2:
        st.metric("📦 分塊總數", stats.get("total_chunks", 0))
    with col3:
        st.metric("🔑 關鍵字總數", stats.get("total_keywords", 0))
    with col4:
        st.metric("📊 向量狀態", "✅" if stats.get("vector_enabled") else "❌")
except Exception as e:
    st.warning(f"無法載入統計: {e}")

st.markdown("---")

# Tab 頁面
tab_upload, tab_docs, tab_config, tab_tokens = st.tabs([
    "📤 檔案上傳", "📋 文件管理", "⚙️ 系統設定", "💰 Token 統計"
])

# =================== Tab 1: 檔案上傳 (建議 6 + 7) ===================
with tab_upload:
    st.subheader("📤 檔案上傳與處理")

    # 拖拽上傳區 (建議 6) - 傳入使用者 API Key
    render_file_uploader(
        client,
        api_key=st.session_state.get("admin_api_key", ""),
        base_url=st.session_state.get("admin_base_url", ""),
    )

    # 批次操作區 (建議 8)
    st.markdown("---")
    st.subheader("📦 批次操作")

    col1, col2 = st.columns(2)
    with col1:
        batch_doc_type = st.selectbox(
            "批次文件類型",
            options=["auto", "knowledge", "training", "procedure", "troubleshooting"],
            format_func=lambda x: {
                "auto": "🤖 自動偵測",
                "knowledge": "📚 知識文件",
                "training": "🎓 教育訓練",
                "procedure": "📋 日常手順",
                "troubleshooting": "🔧 異常解析",
            }[x],
        )
    with col2:
        batch_action = st.selectbox(
            "批次操作",
            options=["reindex", "update_metadata", "validate"],
            format_func=lambda x: {
                "reindex": "🔄 重新索引",
                "update_metadata": "📝 更新元資料",
                "validate": "✅ 驗證完整性",
            }[x],
        )

    if st.button("🚀 執行批次操作", use_container_width=True, type="primary"):
        st.info(f"⏳ 正在執行 {batch_action}...")
        # 呼叫後端批次 API
        result = client._request(
            "POST",
            f"/api/v1/admin/batch/{batch_action}",
            json={"doc_type": batch_doc_type},
        )
        if result and result.get("status") == "success":
            st.success(f"✅ 批次操作完成: {result.get('message', '')}")
        else:
            st.warning("⚠️ 批次操作完成 (部分結果可能需要手動確認)")

# =================== Tab 2: 文件管理 ===================
with tab_docs:
    st.subheader("📋 已入庫文件列表")

    try:
        docs = client.list_documents()

        if docs:
            # 轉為 DataFrame 展示
            df = pd.DataFrame(docs)
            display_cols = []
            for c in ["id", "file_name", "doc_type", "chunk_count", "created_at", "status"]:
                if c in df.columns:
                    display_cols.append(c)

            if display_cols:
                # 搜尋/過濾
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    search_text = st.text_input("🔍 搜尋文件名", placeholder="輸入關鍵字過濾")
                with col2:
                    if "doc_type" in df.columns:
                        type_filter = st.selectbox("📁 類型", ["全部"] + sorted(df["doc_type"].unique().tolist()))
                    else:
                        type_filter = "全部"
                with col3:
                    sort_col = st.selectbox("排序", display_cols)

                # 過濾
                filtered_df = df.copy()
                if search_text:
                    filtered_df = filtered_df[
                        filtered_df["file_name"].str.contains(search_text, case=False, na=False)
                    ]
                if type_filter != "全部" and "doc_type" in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df["doc_type"] == type_filter]

                # 排序
                if sort_col in filtered_df.columns:
                    filtered_df = filtered_df.sort_values(sort_col, ascending=False)

                st.dataframe(
                    filtered_df[display_cols],
                    use_container_width=True,
                    hide_index=True,
                    height=400,
                )

                st.caption(f"顯示 {len(filtered_df)} / {len(df)} 筆文件")

                # 刪除操作
                st.markdown("---")
                st.subheader("🗑️ 刪除文件")
                if "id" in df.columns:
                    del_id = st.number_input("輸入文件 ID", min_value=1, step=1)
                    if st.button("刪除文件", type="secondary"):
                        result = client.delete_document(int(del_id))
                        if result.get("status") == "success":
                            st.success(f"✅ 已刪除文件 ID={del_id}")
                            st.rerun()
                        else:
                            st.error(f"❌ 刪除失敗: {result.get('message', 'unknown error')}")
            else:
                st.info("📄 文件資料格式無法辨識")
        else:
            st.info("📭 資料庫中尚無文件")
    except Exception as e:
        st.error(f"❌ 載入文件失敗: {e}")

# =================== Tab 3: 系統設定 ===================
with tab_config:
    st.subheader("⚙️ 系統設定")

    try:
        config = client.get_config()

        if config:
            # 以表格展示可修改的設定
            config_items = {}

            # 分類整理設定
            general_cfg = {}
            model_cfg = {}
            search_cfg = {}

            for key, value in config.items():
                if "model" in key.lower() or "llm" in key.lower():
                    model_cfg[key] = value
                elif "search" in key.lower() or "vector" in key.lower():
                    search_cfg[key] = value
                else:
                    general_cfg[key] = value

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### 🔧 一般設定")
                for key, value in general_cfg.items():
                    if isinstance(value, bool):
                        config_items[key] = st.checkbox(key, value=value, key=f"cfg_{key}")
                    elif isinstance(value, (int, float)):
                        config_items[key] = st.number_input(key, value=value, key=f"cfg_{key}")
                    elif isinstance(value, str):
                        config_items[key] = st.text_input(key, value=value, key=f"cfg_{key}")

                st.markdown("#### 🔍 搜尋設定")
                for key, value in search_cfg.items():
                    if isinstance(value, bool):
                        config_items[key] = st.checkbox(key, value=value, key=f"cfg_{key}")
                    elif isinstance(value, (int, float)):
                        config_items[key] = st.number_input(key, value=value, key=f"cfg_{key}")
                    elif isinstance(value, str):
                        config_items[key] = st.text_input(key, value=value, key=f"cfg_{key}")

            with col2:
                st.markdown("#### 🤖 模型設定")
                for key, value in model_cfg.items():
                    if isinstance(value, bool):
                        config_items[key] = st.checkbox(key, value=value, key=f"cfg_{key}")
                    elif isinstance(value, (int, float)):
                        config_items[key] = st.number_input(key, value=value, key=f"cfg_{key}")
                    elif isinstance(value, str):
                        config_items[key] = st.text_input(key, value=value, key=f"cfg_{key}")

            st.markdown("---")
            if st.button("💾 儲存設定", type="primary", use_container_width=True):
                result = client.update_config(config_items)
                if result.get("status") == "success":
                    st.success("✅ 設定已更新")
                else:
                    st.error(f"❌ 更新失敗: {result.get('message', '')}")
        else:
            st.info("無法載入系統設定")
    except Exception as e:
        st.error(f"❌ 載入設定失敗: {e}")

# =================== Tab 4: Token 統計 (建議 9) ===================
with tab_tokens:
    st.subheader("💰 Token 使用統計")

    try:
        token_data = client.get_token_stats()

        if token_data:
            # 摘要指標
            summary = token_data.get("summary", {})
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📈 總 Token", f"{summary.get('total_tokens', 0):,}")
            with col2:
                st.metric("📊 總請求數", f"{summary.get('total_requests', 0):,}")
            with col3:
                st.metric("💵 預估費用", f"${summary.get('estimated_cost', 0):.4f}")
            with col4:
                st.metric("📅 今日 Token", f"{summary.get('today_tokens', 0):,}")

            st.markdown("---")

            if HAS_PLOTLY:
                # 互動式圖表 (建議 9)
                daily_data = token_data.get("daily", [])
                if daily_data:
                    st.markdown("#### 📊 每日 Token 趨勢")
                    df_daily = pd.DataFrame(daily_data)
                    if "date" in df_daily.columns and "tokens" in df_daily.columns:
                        fig = px.bar(
                            df_daily,
                            x="date",
                            y="tokens",
                            title="每日 Token 使用量",
                            labels={"date": "日期", "tokens": "Token 數"},
                            color_discrete_sequence=["#4F46E5"],
                        )
                        fig.update_layout(
                            height=350,
                            margin=dict(l=20, r=20, t=40, b=20),
                        )
                        st.plotly_chart(fig, use_container_width=True)

                # 分佈圖
                by_model = token_data.get("by_model", [])
                by_operation = token_data.get("by_operation", [])

                col1, col2 = st.columns(2)

                with col1:
                    if by_model:
                        st.markdown("#### 🤖 模型使用分佈")
                        df_model = pd.DataFrame(by_model)
                        if "model" in df_model.columns and "tokens" in df_model.columns:
                            fig = px.pie(
                                df_model,
                                names="model",
                                values="tokens",
                                title="各模型 Token 佔比",
                            )
                            fig.update_layout(height=300)
                            st.plotly_chart(fig, use_container_width=True)

                with col2:
                    if by_operation:
                        st.markdown("#### ⚡ 操作類型分佈")
                        df_op = pd.DataFrame(by_operation)
                        if "operation" in df_op.columns and "tokens" in df_op.columns:
                            fig = px.pie(
                                df_op,
                                names="operation",
                                values="tokens",
                                title="各操作 Token 佔比",
                            )
                            fig.update_layout(height=300)
                            st.plotly_chart(fig, use_container_width=True)

                # Top 檔案
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
                            title="最消耗 Token 的文件",
                            labels={"tokens": "Token 數", "file_name": "檔案名稱"},
                            color_discrete_sequence=["#10B981"],
                        )
                        fig.update_layout(
                            height=350,
                            margin=dict(l=20, r=20, t=40, b=20),
                            yaxis={"categoryorder": "total ascending"},
                        )
                        st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("📦 請安裝 plotly 以啟用互動圖表: `pip install plotly`")

                # Fallback: 表格
                daily_data = token_data.get("daily", [])
                if daily_data:
                    st.markdown("#### 📊 每日 Token (表格)")
                    st.dataframe(pd.DataFrame(daily_data), use_container_width=True)
        else:
            st.info("📭 尚無 Token 使用紀錄")
    except Exception as e:
        st.error(f"❌ 載入 Token 統計失敗: {e}")

# 底部操作
st.markdown("---")
st.caption("📁 管理後台 v2.0 | 支援拖曳上傳、批次操作、互動式圖表")
