"""
AI Expert System - Admin Page (管理介面) v4.0.0

重構項目（依 organizing-streamlit-code + optimizing-streamlit-performance skill）:
- 拆分至 components/admin/ 子模組：doc_manager, token_charts, health_monitor, config_form, gdpr_panel
- 本檔僅負責側邊欄 + Tab layout 組裝
- 原 681 行  ~200 行（UI 編排） + 5 個元件模組
- use_container_width  width="stretch" (Streamlit 1.50+)
- st.radio  st.segmented_control (choosing-streamlit-selection-widgets skill)
- Material icons 替代 Emoji (improving-streamlit-design skill)
- border=True on metrics (building-streamlit-dashboards skill)
"""

import streamlit as st
import logging

from config import API_BASE_URL
from client.api_client import APIClient
from components.uploader import render_file_uploader
from components.admin import (
    render_document_manager,
    render_token_charts,
    render_health_tab,
    render_config_tab,
    render_gdpr_panel,
)
from utils.cache import (
    cached_health_check,
    cached_detailed_health,
    cached_get_stats,
    cached_list_documents,
)
from utils.models import AVAILABLE_MODELS

logger = logging.getLogger(__name__)

# API Client（由 entrypoint 統一初始化）
client: APIClient = st.session_state.api_client


# ========== 側邊欄 ==========
with st.sidebar:
    st.title(":material/folder: 管理設定")

    # API 設定（BYOK）
    st.subheader(":material/key: API 設定")
    st.session_state.setdefault("admin_api_key", "")
    st.session_state.setdefault("admin_base_url", "http://innoai.cminl.oa/agency/proxy/openai/platform")
    st.session_state.setdefault("admin_available_models", AVAILABLE_MODELS)

    with st.form("admin_byok_form", clear_on_submit=False):
        admin_api_key = st.text_input(
            "API Key",
            value=st.session_state.admin_api_key,
            type="password",
            help="上傳檔案處理時使用您的 API Key（入庫需要 Embedding）",
        )
        admin_base_url = st.text_input(
            "Base URL",
            value=st.session_state.admin_base_url,
            help="企業 API Proxy 端點 URL",
        )
        admin_submitted = st.form_submit_button(":material/vpn_key: 驗證 API Key", width="stretch")

    st.session_state.setdefault("admin_verified", False)

    if admin_submitted:
        st.session_state.admin_api_key = admin_api_key
        st.session_state.admin_base_url = admin_base_url
        if admin_api_key:
            result = client.verify_api_key(api_key=admin_api_key, base_url=admin_base_url)
            if result.get("status") == "valid":
                client.set_user_identity(api_key=admin_api_key)
                st.session_state.admin_verified = True
                models = result.get("available_models", [])
                if models and isinstance(models[0], dict) and "model_id" in models[0]:
                    st.session_state.admin_available_models = models
                st.success(" 驗證成功")
            else:
                st.error(f" 驗證失敗: {result.get('message', '')}")
        else:
            st.error("請先輸入 API Key")

    if st.session_state.admin_verified:
        st.success(" 已驗證")
    elif st.session_state.admin_api_key:
        st.caption(":material/key: 已輸入 Key，請點擊驗證")
    else:
        st.warning(" 請輸入 API Key 並驗證（BYOK 模式）")

    # 後端健康（集中快取）
    health = cached_health_check(API_BASE_URL)
    if health.get("status") == "healthy":
        st.badge("後端正常", icon=":material/check_circle:", color="green")
    else:
        st.badge("後端離線", icon=":material/error:", color="red")

    # 詳細健康資訊
    try:
        detailed_health = cached_detailed_health(API_BASE_URL)
        if detailed_health.get("databases"):
            dbs = detailed_health["databases"]
            for db_name, db_info in dbs.items():
                status_icon = ":material/check:" if db_info.get("ok") else ":material/close:"
                wal_icon = "WAL" if db_info.get("wal_mode") else "非WAL"
                st.caption(
                    f"{status_icon} {db_name} | {wal_icon} | {db_info.get('latency_ms', '?')}ms"
                )
    except Exception:
        pass

    # 模型/分析模式已移至「 系統設定」Tab
    st.session_state.setdefault("admin_analysis_mode", "auto")
    st.caption(":material/info: 模型選擇與分析模式請至「系統設定」Tab 調整")

    # 快速操作
    st.subheader(":material/build: 快速操作")
    if st.button(":material/refresh: 重新載入資料", width="stretch"):
        cached_health_check.clear()
        cached_detailed_health.clear()
        cached_get_stats.clear()
        cached_list_documents.clear()
        st.rerun()


# ========== 主畫面 ==========
st.title(":material/folder: 管理後台")

# 頂部指標摘要
try:
    stats = cached_get_stats(API_BASE_URL)
    with st.container(horizontal=True):
        st.metric(":material/description: 文件總數", stats.get("total_documents", 0), border=True)
        st.metric(":material/inventory_2: 分塊總數", stats.get("total_chunks", 0), border=True)
        st.metric(":material/key: 關鍵字總數", stats.get("total_keywords", 0), border=True)
        st.metric(":material/memory: 向量狀態", "" if stats.get("vector_enabled") else "", border=True)
except Exception as e:
    st.warning(f"無法載入統計: {e}")

# Tab 頁面
tab_upload, tab_docs, tab_config, tab_tokens, tab_health = st.tabs([
    ":material/upload: 檔案上傳",
    ":material/description: 文件管理",
    ":material/settings: 系統設定",
    ":material/payments: Token 統計",
    ":material/health_and_safety: 系統健康",
])

# Tab 1: 檔案上傳
with tab_upload:
    st.subheader(":material/upload: 檔案上傳與處理")

    render_file_uploader(
        client,
        api_key=st.session_state.get("admin_api_key", ""),
        base_url=st.session_state.get("admin_base_url", ""),
        analysis_mode=st.session_state.get("admin_analysis_mode", "auto"),
    )

    st.subheader(":material/inventory_2: 批次操作")

    col1, col2 = st.columns(2)
    with col1:
        batch_doc_type = st.selectbox(
            "批次文件類型",
            options=["auto", "knowledge", "training", "procedure", "troubleshooting"],
            format_func=lambda x: {
                "auto": ":material/smart_toy: 自動偵測",
                "knowledge": ":material/menu_book: 知識文件",
                "training": ":material/school: 教育訓練",
                "procedure": ":material/checklist: 日常手順",
                "troubleshooting": ":material/build: 異常解析",
            }[x],
        )
    with col2:
        batch_action = st.selectbox(
            "批次操作",
            options=["reindex", "update_metadata", "validate"],
            format_func=lambda x: {
                "reindex": ":material/refresh: 重新索引",
                "update_metadata": ":material/edit_note: 更新元資料",
                "validate": ":material/check_circle: 驗證完整性",
            }[x],
        )

    if st.button(":material/play_arrow: 執行批次操作", width="stretch", type="primary"):
        st.info(f" 正在執行 {batch_action}...")
        result = client._request(
            "POST",
            f"/api/v1/admin/batch/{batch_action}",
            json={"doc_type": batch_doc_type},
        )
        if result and result.get("status") == "success":
            st.success(f" 批次操作完成: {result.get('message', '')}")
        else:
            st.warning(" 批次操作完成 (部分結果可能需要手動確認)")

# Tab 2: 文件管理 (@st.fragment)
with tab_docs:
    render_document_manager(client)

# Tab 3: 系統設定
with tab_config:
    render_config_tab(client)

# Tab 4: Token 統計
with tab_tokens:
    render_token_charts(client)

# Tab 5: 系統健康 + GDPR
with tab_health:
    render_health_tab(client)
    render_gdpr_panel(client)

# 底部
st.caption(":material/folder: 管理後台 v4.0.0 | 模組化元件 + 集中快取 + BYOK + Fragment")