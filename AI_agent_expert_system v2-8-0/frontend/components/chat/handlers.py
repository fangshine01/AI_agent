"""
Chat Handlers — 身份驗證、Session CRUD、訊息儲存、工具函式

從 chat.py 拆出，純業務邏輯函式（不含 UI）。
"""

import streamlit as st
import logging
import time

logger = logging.getLogger(__name__)


def verify_and_set_identity(client, api_key: str, username: str, base_url: str):
    """驗證 API Key 並設定 BYOK 身份"""
    with st.spinner(":material/vpn_key: 驗證 API Key 中..."):
        result = client.verify_api_key(
            api_key=api_key,
            username=username,
            base_url=base_url,
        )
    if result.get("status") == "valid":
        client.set_user_identity(api_key=api_key, username=username)
        st.session_state.byok_verified = True
        st.session_state.byok_user_hash = result.get("user_hash", "")
        models = result.get("available_models", [])
        if models:
            if isinstance(models[0], dict) and "model_id" in models[0]:
                st.session_state.available_models = models
            else:
                st.session_state.available_models = [
                    {"display_name": m, "model_id": m, "category": "", "cost_label": "💰"}
                    for m in models
                ]
        st.success(f"✅ 驗證成功！身份: {st.session_state.byok_user_hash}")
        refresh_session_list(client)
    else:
        st.session_state.byok_verified = False
        st.error(f"❌ 驗證失敗: {result.get('message', '未知錯誤')}")


def refresh_session_list(client):
    """重新載入對話歷史列表"""
    if st.session_state.byok_verified:
        result = client.get_sessions()
        if result.get("success"):
            st.session_state.session_list = result.get("sessions", [])


def load_session(client, session_id: str):
    """載入指定 Session 的對話記錄"""
    result = client.get_session_history(session_id)
    if result.get("success"):
        st.session_state.current_session_id = session_id
        st.session_state.messages = [
            {"role": m["role"], "content": m["content"], "tokens": m.get("tokens_used", 0)}
            for m in result.get("messages", [])
        ]
        st.session_state.session_tokens = result.get("total_tokens", 0)


def new_session(client, model_used: str = None):
    """建立新對話 Session，失敗時顯示錯誤提示"""
    result = client.create_session(title="新對話", model_used=model_used)
    if result.get("success"):
        st.session_state.current_session_id = result["session_id"]
        st.session_state.messages = []
        st.session_state.session_tokens = 0
        refresh_session_list(client)
    else:
        err_msg = result.get("message", "未知錯誤")
        logger.error(f"[DB] 建立 Session 失敗: {err_msg}")
        st.toast(f"⚠️ 對話記錄無法建立（{err_msg}），問答功能仍可使用但不會儲存歷史", icon="⚠️")


def save_message_to_history(client, role: str, content: str, model_used: str = None, tokens_used: int = 0):
    """將訊息儲存到後端，失敗時以 toast 通知"""
    if not st.session_state.current_session_id or not st.session_state.byok_verified:
        return
    try:
        result = client.save_message(
            session_id=st.session_state.current_session_id,
            role=role,
            content=content,
            model_used=model_used,
            tokens_used=tokens_used,
        )
        if result.get("status") == "error" or not result.get("success", True):
            err_msg = result.get("message", "未知錯誤")
            logger.warning(f"[DB] 訊息儲存未成功 ({role}): {err_msg}")
            st.toast(f"⚠️ 對話記錄未儲存: {err_msg}", icon="⚠️")
    except Exception as e:
        logger.error(f"[DB] 儲存訊息例外 ({role}): {e}")
        st.toast("⚠️ 對話記錄儲存失敗（網路或後端問題）", icon="⚠️")


def clear_chat():
    """清除對話（on_click callback）"""
    st.session_state.messages = []
    st.session_state.current_session_id = None
    st.session_state.session_tokens = 0


def simulate_stream(text: str):
    """降級處理：將完整文字模擬為 streaming 逐字輸出"""
    words = text.split(" ")
    for i, word in enumerate(words):
        yield word + (" " if i < len(words) - 1 else "")
        time.sleep(0.02)
