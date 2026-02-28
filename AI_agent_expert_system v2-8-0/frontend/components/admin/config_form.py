"""
系統設定表單 — Admin Tab 3

從 admin.py 拆出，負責：
- 檔案分析模式 (text_only / vision / auto)
- 模型選擇 & API 配置
- 儲存設定
"""

import streamlit as st
import logging

from utils.models import format_model_display

logger = logging.getLogger(__name__)


def render_config_tab(client):
    """渲染系統設定 Tab 內容"""
    st.subheader(":material/settings: 系統設定")

    # ---- 區塊 1: 檔案分析模式 ----
    st.markdown("#### :material/description: 檔案上傳分析設定")
    st.caption("此設定決定上傳檔案時使用「純文字」或「含圖分析」模式，影響 Token 消耗量。")

    cfg_analysis_mode = st.segmented_control(
        "預設分析模式",
        options=["text_only", "vision", "auto"],
        format_func=lambda x: {
            "text_only": ":material/text_fields: 純文字",
            "vision": ":material/image: 含圖分析",
            "auto": ":material/smart_toy: 自動判斷",
        }[x],
        default=st.session_state.get("admin_analysis_mode", "auto"),
        key="cfg_analysis_mode_seg",
    )

    mode_desc = {
        "text_only": "適合純文字 Markdown、TXT 文件。跳過 PPT 中的圖片。",
        "vision": "適合含圖片的 PPT、PDF。會使用 Vision 模型，Token 消耗較高。",
        "auto": "智慧判斷檔案是否含圖，自動選擇最佳模式。",
    }
    if cfg_analysis_mode:
        st.caption(mode_desc.get(cfg_analysis_mode, ""))

    # ---- 區塊 2: 模型與 API 設定 ----
    st.markdown("#### :material/smart_toy: 模型與 API 配置")

    try:
        config_resp = client.get_config()
        config_data = config_resp.get("data", config_resp) if config_resp else {}

        _cfg_models = st.session_state.get("admin_available_models", [])
        _cfg_model_ids = [m.get("model_id", "") for m in _cfg_models]

        def _format_model_id(mid):
            return next(
                (format_model_display(m) for m in _cfg_models if m.get("model_id") == mid),
                mid,
            )

        col1, col2 = st.columns(2)
        with col1:
            cfg_base_url = st.text_input(
                "API Base URL",
                value=config_data.get("base_url", "http://innoai.cminl.oa/agency/proxy/openai/platform"),
                key="cfg_base_url",
                help="企業 API Proxy 端點",
            )
            cfg_model_text = st.selectbox(
                "純文字解析模型",
                options=_cfg_model_ids,
                format_func=_format_model_id,
                index=next(
                    (i for i, m in enumerate(_cfg_models)
                     if m.get("model_id") == config_data.get("model_text", "gpt-4o-mini")),
                    1,
                ),
                key="cfg_model_text",
                help="用於純文字內容解析的模型",
            )
        with col2:
            cfg_model_vision = st.selectbox(
                "圖文解析模型",
                options=_cfg_model_ids,
                format_func=_format_model_id,
                index=next(
                    (i for i, m in enumerate(_cfg_models)
                     if m.get("model_id") == config_data.get("model_vision", "gpt-4o")),
                    0,
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
        cfg_analysis_mode = cfg_analysis_mode or "auto"
        st.warning(f"⚠️ 無法載入後端配置: {e}")

    # ---- 儲存 ----
    if st.button(
        ":material/save: 儲存設定",
        type="primary",
        width="stretch",
        key="save_config_btn",
    ):
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
