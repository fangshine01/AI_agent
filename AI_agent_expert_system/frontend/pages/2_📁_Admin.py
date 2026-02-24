"""
AI Expert System - Admin Page (管理介面) v2.3.0
已套用功能:
- BYOK 身份驗證
- 拖曳上傳區 + 分析模式設定（純文字 / 含圖分析）
- 實時處理進度
- 批次操作列表
- 13 模型下拉選擇器（企業 API Proxy 統一端點）
- Token 互動式圖表 (By User Hash)
- 系統健康詳細狀態
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

from client.api_client import APIClient
from config import API_BASE_URL
from components.uploader import render_file_uploader

logger = logging.getLogger(__name__)

# 頁面設定
st.set_page_config(page_title="AI Expert System - 管理後台", page_icon="📁", layout="wide")

# 初始化
if "api_client" not in st.session_state:
    st.session_state.api_client = APIClient(base_url=API_BASE_URL)

client: APIClient = st.session_state.api_client


# ========== 快取與局部重繪函式（減少不必要 API 呼叫與全頁 rerun） ==========

@st.cache_data(ttl=30)
def _cached_health_check(base_url: str) -> dict:
    """30 秒快取後端健康檢查"""
    return APIClient(base_url=base_url).health_check()


@st.cache_data(ttl=30)
def _cached_detailed_health(base_url: str) -> dict:
    """30 秒快取詳細健康資訊"""
    return APIClient(base_url=base_url)._request("GET", "/health/detailed")


@st.cache_data(ttl=60)
def _cached_get_stats(base_url: str) -> dict:
    """60 秒快取統計資料"""
    return APIClient(base_url=base_url).get_stats()


@st.fragment
def _render_document_manager():
    """文件管理列表 — 搜尋/篩選只重繪此 fragment，不觸發全頁 rerun"""
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

            if not display_cols:
                # Fallback to available columns if the expected ones are not found
                display_cols = list(df.columns)

            if display_cols:
                # 搜尋/過濾（fragment 內，逐鍵搜尋只重繪此區塊）
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    search_text = st.text_input("🔍 搜尋文件名", placeholder="輸入關鍵字過濾")
                with col2:
                    if "doc_type" in df.columns:
                        type_filter = st.selectbox("📁 類型", ["全部"] + sorted(df["doc_type"].dropna().unique().tolist()))
                    else:
                        type_filter = "全部"
                with col3:
                    sort_col = st.selectbox("排序", display_cols)

                # 過濾
                filtered_df = df.copy()
                if search_text and "file_name" in filtered_df.columns:
                    filtered_df = filtered_df[
                        filtered_df["file_name"].str.contains(search_text, case=False, na=False)
                    ]
                elif search_text and "filename" in filtered_df.columns:
                    filtered_df = filtered_df[
                        filtered_df["filename"].str.contains(search_text, case=False, na=False)
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
                            st.rerun()  # 全頁 rerun 以更新頂部統計
                        else:
                            st.error(f"❌ 刪除失敗: {result.get('message', 'unknown error')}")
            else:
                st.info("📄 文件資料格式無法辨識 (Data format missing expected columns)")
        else:
            st.info("📭 資料庫中尚無文件")
    except Exception as e:
        st.error(f"❌ 載入文件失敗: {e}")


# ========== 側邊欄 ==========
with st.sidebar:
    st.title("📁 管理設定")

    # API 設定（讓每位使用者輸入自己的 API Key）
    st.subheader("🔑 API 設定")
    if "admin_api_key" not in st.session_state:
        st.session_state.admin_api_key = ""
    if "admin_base_url" not in st.session_state:
        st.session_state.admin_base_url = "http://innoai.cminl.oa/agency/proxy/openai/platform"
    # 企業 API 統一端點，支援 OpenAI / Google / Azure，不需選擇 provider
    if "admin_available_models" not in st.session_state:
        # 預設 27 個模型清單（依 GPT_support.md，v2.4.0，驗證後會被後端回傳清單覆蓋）
        st.session_state.admin_available_models = [
            # ===== OpenAI 平台 =====
            {"display_name": "OpenAI-GPT-4o",         "model_id": "gpt-4o",               "category": "OpenAI 標準", "cost_label": "💰💰"},
            {"display_name": "OpenAI-GPT-4o-mini",     "model_id": "gpt-4o-mini",          "category": "OpenAI 標準", "cost_label": "💰"},
            {"display_name": "OpenAI-GPT-4.1",         "model_id": "gpt-4.1",              "category": "OpenAI 進階", "cost_label": "💰💰💰"},
            {"display_name": "OpenAI-GPT-4.1-Mini",    "model_id": "gpt-4.1-mini",         "category": "OpenAI 輕量", "cost_label": "💰"},
            {"display_name": "OpenAI-GPT-4-Turbo",     "model_id": "gpt-4-turbo-preview",  "category": "OpenAI 舊版", "cost_label": "💰💰💰"},
            {"display_name": "OpenAI-GPT-4-Vision",    "model_id": "gpt-4-vision-preview", "category": "OpenAI 視覺", "cost_label": "💰💰💰"},
            {"display_name": "OpenAI-O1",              "model_id": "o1",                   "category": "OpenAI 推理", "cost_label": "💰💰💰"},
            {"display_name": "OpenAI-O1-Mini",         "model_id": "o1-mini",              "category": "OpenAI 推理", "cost_label": "💰💰"},
            {"display_name": "OpenAI-O3-mini",         "model_id": "o3-mini",              "category": "OpenAI 推理", "cost_label": "💰💰"},
            {"display_name": "OpenAI-O4-Mini",         "model_id": "o4-mini",              "category": "OpenAI 推理", "cost_label": "💰💰"},
            {"display_name": "GPT-5-mini",             "model_id": "gpt-5-mini",           "category": "OpenAI 未來", "cost_label": "💰💰"},
            {"display_name": "GPT-5.1",                "model_id": "gpt-5.1",              "category": "OpenAI 未來", "cost_label": "💰💰💰"},
            # ===== Google 平台 =====
            {"display_name": "Google-Gemini-2.5-Pro",       "model_id": "gemini-2.5-pro",             "category": "Google 進階", "cost_label": "💰💰💰"},
            {"display_name": "Google-Gemini-2.5-Flash",      "model_id": "gemini-2.5-flash",           "category": "Google 標準", "cost_label": "💰"},
            {"display_name": "Google-Gemini-2.5-Flash-Lite", "model_id": "gemini-2.5-flash-lite",      "category": "Google 輕量", "cost_label": "💰"},
            {"display_name": "Google-Gemini-2.0-Flash",      "model_id": "gemini-2.0-flash",           "category": "Google 標準", "cost_label": "💰"},
            {"display_name": "Google-Gemini-2.0-Flash-Lite", "model_id": "gemini-2.0-flash-lite",      "category": "Google 輕量", "cost_label": "💰"},
            {"display_name": "Google-Gemini-1.5-Flash",      "model_id": "gemini-1.5-flash-latest",    "category": "Google 舊版", "cost_label": "💰"},
            {"display_name": "Gemini-3-Pro-Preview",         "model_id": "gemini-3-pro-preview",       "category": "Google 未來", "cost_label": "💰💰💰"},
            {"display_name": "Gemini-3-Flash-Preview",       "model_id": "gemini-3-flash-preview",     "category": "Google 未來", "cost_label": "💰💰"},
            {"display_name": "Gemini-2.5-Flash-Image",       "model_id": "gemini-2.5-flash-image",     "category": "Google 視覺", "cost_label": "💰💰"},
            {"display_name": "Gemini-3-Pro-Image",           "model_id": "gemini-3-pro-image-preview", "category": "Google 視覺", "cost_label": "💰💰💰"},
            # ===== Azure 平台 =====
            {"display_name": "Azure-GPT-4o",        "model_id": "gpt-4o",      "category": "Azure 標準", "cost_label": "💰💰"},
            {"display_name": "Azure-GPT-4o-mini",   "model_id": "gpt-4o-mini", "category": "Azure 標準", "cost_label": "💰"},
            {"display_name": "Azure-GPT-4o-0806",   "model_id": "gpt-4o-0806", "category": "Azure 標準", "cost_label": "💰💰"},
            {"display_name": "Azure-GPT-4.1",       "model_id": "gpt-4.1",     "category": "Azure 進階", "cost_label": "💰💰💰"},
            {"display_name": "Azure-GPT-4.1-Mini",  "model_id": "gpt-4.1-mini","category": "Azure 輕量", "cost_label": "💰"},
            {"display_name": "Azure-O1-Mini",        "model_id": "o1-mini",     "category": "Azure 推理", "cost_label": "💰💰"},
            {"display_name": "Azure-GPT-O4-Mini",   "model_id": "o4-mini",     "category": "Azure 推理", "cost_label": "💰💰"},
            {"display_name": "Azure-GPT-4-Turbo",   "model_id": "gpt-4",       "category": "Azure 舊版", "cost_label": "💰💰💰"},
            {"display_name": "Azure-GPT-5.1",       "model_id": "gpt-5.1",     "category": "Azure 未來", "cost_label": "💰💰💰"},
        ]

    # st.form 包裝：只在按下「驗證」時才觸發 rerun，避免逐鍵刷新
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
        admin_submitted = st.form_submit_button("🔐 驗證 API Key", use_container_width=True)

    # BYOK 驗證按鈕
    if "admin_verified" not in st.session_state:
        st.session_state.admin_verified = False

    # form 外處理驗證邏輯（submit 時才更新 session_state）
    if admin_submitted:
        st.session_state.admin_api_key = admin_api_key
        st.session_state.admin_base_url = admin_base_url
        if admin_api_key:
            result = client.verify_api_key(
                api_key=admin_api_key,
                base_url=admin_base_url,
            )
            if result.get("status") == "valid":
                client.set_user_identity(api_key=admin_api_key)
                st.session_state.admin_verified = True
                # 更新可用模型清單
                models = result.get("available_models", [])
                if models and isinstance(models[0], dict) and "model_id" in models[0]:
                    st.session_state.admin_available_models = models
                st.success("✅ 驗證成功")
            else:
                st.error(f"❌ 驗證失敗: {result.get('message', '')}")
        else:
            st.error("請先輸入 API Key")

    if st.session_state.admin_verified:
        st.success("✅ 已驗證")
    elif st.session_state.admin_api_key:
        st.info("🔑 已輸入 Key，請點擊驗證")
    else:
        st.warning("⚠️ 請輸入您的 API Key 並驗證（系統採用 BYOK 模式，所有用戶必須使用自己的 Key）")

    st.markdown("---")

    # 後端健康（@st.cache_data TTL=30s 避免頻繁打後端）
    health = _cached_health_check(API_BASE_URL)
    if health.get("status") == "healthy":
        st.success("🟢 後端連線正常")
    else:
        st.error("🔴 後端離線")

    # 詳細健康資訊（快取 30 秒）
    try:
        detailed_health = _cached_detailed_health(API_BASE_URL)
        if detailed_health.get("databases"):
            dbs = detailed_health["databases"]
            for db_name, db_info in dbs.items():
                status_icon = "🟢" if db_info.get("ok") else "🔴"
                wal_icon = "✅" if db_info.get("wal_mode") else "❌"
                st.caption(f"{status_icon} {db_name} | WAL: {wal_icon} | {db_info.get('latency_ms', '?')}ms")
    except Exception:
        pass

    st.markdown("---")

    # 模型選擇器（13 個模型）
    st.subheader("🤖 模型選擇")
    _admin_models = st.session_state.admin_available_models

    def _format_admin_model(m):
        """格式化模型下拉選單顯示文字"""
        if isinstance(m, dict):
            cost = m.get("cost_label", "")
            cat = m.get("category", "")
            name = m.get("display_name", m.get("model_id", ""))
            return f"{cost} {name}  ({cat})" if cat else f"{cost} {name}"
        return str(m)

    admin_selected_model = st.selectbox(
        "處理模型",
        options=_admin_models,
        format_func=_format_admin_model,
        help="檔案入庫解析時使用的 AI 模型",
        key="admin_model_select",
    )
    # 取得選中模型的 model_id
    if isinstance(admin_selected_model, dict):
        admin_model_id = admin_selected_model.get("model_id", "gpt-4o-mini")
    else:
        admin_model_id = str(admin_selected_model)

    st.markdown("---")

    # 檔案分析模式設定
    st.subheader("📄 分析模式")
    if "admin_analysis_mode" not in st.session_state:
        st.session_state.admin_analysis_mode = "auto"

    analysis_mode = st.radio(
        "檔案上傳分析方式",
        options=["text_only", "vision", "auto"],
        format_func=lambda x: {
            "text_only": "📝 純文字分析（省錢、適合文字為主的文件）",
            "vision": "🖼️ 含圖分析（解析 PPT/PDF 中的圖片內容）",
            "auto": "🤖 自動判斷（有圖用 Vision，無圖用純文字）",
        }[x],
        index=["text_only", "vision", "auto"].index(st.session_state.admin_analysis_mode),
        key="admin_analysis_mode_radio",
        help="純文字模式較省 Token；含圖分析可提取圖表資訊但比較耗費 Token",
    )
    st.session_state.admin_analysis_mode = analysis_mode

    st.markdown("---")

    # 快速操作
    st.subheader("🔧 快速操作")
    if st.button("🔄 重新載入資料", use_container_width=True):
        # 清除所有快取，強制重新載入
        _cached_health_check.clear()
        _cached_detailed_health.clear()
        _cached_get_stats.clear()
        st.rerun()

# ========== 主畫面 ==========
st.title("📁 管理後台")

# 頂部指標摘要
try:
    stats = _cached_get_stats(API_BASE_URL)
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
tab_upload, tab_docs, tab_config, tab_tokens, tab_health = st.tabs([
    "📤 檔案上傳", "📋 文件管理", "⚙️ 系統設定", "💰 Token 統計", "🏥 系統健康"
])

# =================== Tab 1: 檔案上傳 (建議 6 + 7) ===================
with tab_upload:
    st.subheader("📤 檔案上傳與處理")

    # 拖拽上傳區 (建議 6) - 傳入使用者 API Key 及分析模式
    render_file_uploader(
        client,
        api_key=st.session_state.get("admin_api_key", ""),
        base_url=st.session_state.get("admin_base_url", ""),
        analysis_mode=st.session_state.get("admin_analysis_mode", "auto"),
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

# =================== Tab 2: 文件管理 (@st.fragment 局部重繪) ===================
with tab_docs:
    _render_document_manager()

# =================== Tab 3: 系統設定 ===================
with tab_config:
    st.subheader("⚙️ 系統設定")

    # --- 區塊 1: 檔案分析模式設定 ---
    st.markdown("#### 📄 檔案上傳分析設定")
    st.info("💡 此設定決定上傳檔案時使用「純文字」或「含圖分析」模式，影響 Token 消耗量。")

    col_mode, col_preview = st.columns([2, 1])
    with col_mode:
        cfg_analysis_mode = st.radio(
            "預設分析模式",
            options=["text_only", "vision", "auto"],
            format_func=lambda x: {
                "text_only": "📝 純文字分析 — 僅解析文字內容，Token 消耗低",
                "vision": "🖼️ 含圖分析 — 解析 PPT/PDF 中的圖片，Token 消耗高",
                "auto": "🤖 自動判斷 — 有圖用 Vision，無圖用純文字",
            }[x],
            index=["text_only", "vision", "auto"].index(
                st.session_state.get("admin_analysis_mode", "auto")
            ),
            key="cfg_analysis_mode_radio",
        )
    with col_preview:
        st.markdown("**模式說明**")
        mode_desc = {
            "text_only": "適合純文字 Markdown、TXT 文件。\n跳過 PPT 中的圖片。",
            "vision": "適合含圖片的 PPT、PDF。\n會使用 Vision 模型提取圖片內容，Token 消耗較高。",
            "auto": "智慧判斷檔案是否含圖，\n自動選擇最佳模式。",
        }
        st.caption(mode_desc.get(cfg_analysis_mode, ""))

    st.markdown("---")

    # --- 區塊 2: 模型與 API 設定（顯示當前後端配置） ---
    st.markdown("#### 🤖 模型與 API 配置")

    try:
        config_resp = client.get_config()
        config_data = config_resp.get("data", config_resp) if config_resp else {}

        col1, col2 = st.columns(2)
        with col1:
            cfg_base_url = st.text_input(
                "API Base URL",
                value=config_data.get("base_url", "http://innoai.cminl.oa/agency/proxy/openai/platform"),
                key="cfg_base_url",
                help="企業 API Proxy 端點，同時支援 OpenAI 與 Gemini 模型",
            )
            cfg_model_text = st.selectbox(
                "純文字解析模型",
                options=[m.get("model_id", "") for m in st.session_state.admin_available_models],
                format_func=lambda mid: next(
                    (f"{m.get('cost_label', '')} {m.get('display_name', mid)}  ({m.get('category', '')})"
                     for m in st.session_state.admin_available_models if m.get("model_id") == mid),
                    mid
                ),
                index=next(
                    (i for i, m in enumerate(st.session_state.admin_available_models)
                     if m.get("model_id") == config_data.get("model_text", "gpt-4o-mini")),
                    1  # 預設 OpenAI-GPT-4o-mini (index 1)
                ),
                key="cfg_model_text",
                help="用於純文字內容解析的模型",
            )
        with col2:
            cfg_model_vision = st.selectbox(
                "圖文解析模型",
                options=[m.get("model_id", "") for m in st.session_state.admin_available_models],
                format_func=lambda mid: next(
                    (f"{m.get('cost_label', '')} {m.get('display_name', mid)}  ({m.get('category', '')})"
                     for m in st.session_state.admin_available_models if m.get("model_id") == mid),
                    mid
                ),
                index=next(
                    (i for i, m in enumerate(st.session_state.admin_available_models)
                     if m.get("model_id") == config_data.get("model_vision", "gpt-4o")),
                    0  # 預設 OpenAI-GPT-4o (index 0)
                ),
                key="cfg_model_vision",
                help="用於含圖片內容解析的模型（需支援 Vision）",
            )
            has_key_icon = "✅" if config_data.get("has_api_key") else "⚠️ 未設定"
            st.metric("系統級 API Key", has_key_icon)

    except Exception as e:
        cfg_base_url = ""
        cfg_model_text = "gpt-4o-mini"
        cfg_model_vision = "gpt-4o"
        cfg_analysis_mode = "auto"
        st.warning(f"⚠️ 無法載入後端配置: {e}")

    st.markdown("---")

    # 儲存按鈕
    if st.button("💾 儲存設定", type="primary", use_container_width=True, key="save_config_btn"):
        try:
            save_payload = {
                "base_url": cfg_base_url,
                "model_text": cfg_model_text,
                "model_vision": cfg_model_vision,
                "analysis_mode": cfg_analysis_mode,
            }
            result = client.update_config(save_payload)
            if result.get("success") or result.get("status") == "success":
                st.session_state.admin_analysis_mode = cfg_analysis_mode
                st.success("✅ 設定已更新")
            else:
                st.error(f"❌ 更新失敗: {result.get('message', '')}")
        except Exception as e:
            st.error(f"❌ 儲存設定失敗: {e}")

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

                # By User Hash（按使用者雜湊分組）
                by_user = token_data.get("by_user", [])
                if by_user:
                    st.markdown("#### 👤 使用者 Token 統計 (By User Hash)")
                    df_user = pd.DataFrame(by_user)
                    if "user_id" in df_user.columns and "tokens" in df_user.columns:
                        fig = px.bar(
                            df_user.head(20),
                            x="user_id",
                            y="tokens",
                            title="各使用者 Token 使用量",
                            labels={"user_id": "使用者 (Hash)", "tokens": "Token 數"},
                            color_discrete_sequence=["#F59E0B"],
                        )
                        fig.update_layout(
                            height=350,
                            margin=dict(l=20, r=20, t=40, b=20),
                            xaxis_tickangle=-45,
                        )
                        st.plotly_chart(fig, use_container_width=True)

                        # 使用者明細表格
                        with st.expander("📋 使用者明細表格"):
                            st.dataframe(
                                df_user.rename(columns={
                                    "user_id": "使用者 Hash",
                                    "tokens": "Token",
                                    "requests": "請求數",
                                }),
                                use_container_width=True,
                                hide_index=True,
                            )

                # By Hour（按小時分組 - 監控尖峰時段）
                by_hour = token_data.get("by_hour", [])
                if by_hour:
                    st.markdown("#### 🕐 每小時使用量 (Peak Hour 分析)")
                    df_hour = pd.DataFrame(by_hour)
                    if "hour" in df_hour.columns and "tokens" in df_hour.columns:
                        fig = px.bar(
                            df_hour,
                            x="hour",
                            y="tokens",
                            title="24 小時 Token 分佈",
                            labels={"hour": "小時 (0-23)", "tokens": "Token 數"},
                            color_discrete_sequence=["#8B5CF6"],
                        )
                        fig.update_layout(
                            height=300,
                            margin=dict(l=20, r=20, t=40, b=20),
                        )
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

# =================== Tab 5: 系統健康 ===================
with tab_health:
    st.subheader("🏥 系統健康監控")

    try:
        detailed = client._request("GET", "/health/detailed")

        # 整體狀態
        overall_status = detailed.get("status", "unknown")
        if overall_status == "healthy":
            st.success("🟢 系統整體健康")
        elif overall_status == "degraded":
            st.warning("🟡 系統部分降級")
        else:
            st.error("🔴 系統異常")

        # 服務版本 & 運行時間
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🏷️ 版本", detailed.get("version", "N/A"))
        with col2:
            uptime = detailed.get("uptime_seconds", 0)
            hours = int(uptime // 3600)
            mins = int((uptime % 3600) // 60)
            st.metric("⏱️ 運行時間", f"{hours}h {mins}m")
        with col3:
            st.metric("💾 磁碟空間", f"{detailed.get('disk_free_gb', '?')} GB")

        st.markdown("---")

        # 資料庫狀態
        dbs = detailed.get("databases", {})
        if dbs:
            st.markdown("#### 📀 資料庫狀態")
            for db_name, db_info in dbs.items():
                ok = db_info.get("ok", False)
                icon = "🟢" if ok else "🔴"
                wal = "✅ WAL" if db_info.get("wal_mode") else "⚠️ 非 WAL"
                latency = db_info.get("latency_ms", "?")
                size = db_info.get("size_mb", "?")
                st.markdown(f"{icon} **{db_name}** | {wal} | 延遲: {latency}ms | 大小: {size} MB")

        # 目錄狀態
        dirs = detailed.get("directories", {})
        if dirs:
            st.markdown("#### 📂 目錄狀態")
            for dir_name, dir_info in dirs.items():
                exists = dir_info.get("exists", False)
                icon = "✅" if exists else "❌"
                count = dir_info.get("file_count", "?")
                st.markdown(f"{icon} **{dir_name}** | 檔案數: {count}")

        # 活躍 Session
        sessions = detailed.get("active_sessions", {})
        if sessions:
            st.markdown("#### 👥 活躍連線")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("活躍 Session", sessions.get("count", 0))
            with col2:
                st.metric("不重複使用者", sessions.get("unique_users", 0))

    except Exception as e:
        st.error(f"❌ 無法載入健康資訊: {e}")
        st.info("請確認後端服務已啟動且 /health/detailed 端點可用")

    # GDPR 資料管理區塊
    st.markdown("---")
    st.subheader("🔒 個人資料管理 (GDPR)")

    if st.session_state.get("admin_verified"):
        col_export, col_stats, col_delete = st.columns(3)

        with col_export:
            if st.button("📥 匯出我的資料", use_container_width=True, key="gdpr_export_btn"):
                try:
                    data = client.export_user_data()
                    if data:
                        import json
                        st.download_button(
                            label="⬇️ 下載 JSON",
                            data=json.dumps(data, ensure_ascii=False, indent=2),
                            file_name="my_data_export.json",
                            mime="application/json",
                            key="gdpr_download_btn",
                        )
                    else:
                        st.info("沒有找到個人資料")
                except Exception as e:
                    st.error(f"匯出失敗: {e}")

        with col_stats:
            if st.button("📊 我的統計", use_container_width=True, key="gdpr_stats_btn"):
                try:
                    stats = client.get_user_stats()
                    if stats:
                        st.json(stats)
                    else:
                        st.info("尚無統計資料")
                except Exception as e:
                    st.error(f"取得統計失敗: {e}")

        with col_delete:
            st.markdown("**⚠️ 危險操作**")
            confirm = st.checkbox("我確認要刪除所有個人資料", key="gdpr_delete_confirm")
            if st.button("🗑️ 刪除我的資料", use_container_width=True, type="primary",
                         disabled=not confirm, key="gdpr_delete_btn"):
                try:
                    result = client.delete_user_data(confirm=True)
                    if result.get("status") == "deleted":
                        st.success("✅ 所有個人資料已永久刪除")
                    else:
                        st.error(f"刪除失敗: {result.get('message', '')}")
                except Exception as e:
                    st.error(f"刪除失敗: {e}")
    else:
        st.info("🔑 請先在側邊欄驗證 API Key 後，才能管理個人資料")

# 底部操作
st.markdown("---")
st.caption("📁 管理後台 v2.3.0 | 支援 BYOK 驗證、13 模型選擇、分析模式設定、拖曳上傳、互動式圖表")
