"""
GDPR 個人資料管理面板

從 admin.py 拆出，負責：
- 匯出個人資料
- 個人統計
- 刪除個人資料（確認流程）
"""

import json
import streamlit as st
import logging

logger = logging.getLogger(__name__)


def render_gdpr_panel(client):
    """渲染 GDPR 資料管理區塊"""
    st.subheader(":material/lock: 個人資料管理 (GDPR)")

    if not st.session_state.get("admin_verified"):
        st.caption("請先在側邊欄驗證 API Key 後，才能管理個人資料")
        return

    col_export, col_stats, col_delete = st.columns(3)

    with col_export:
        if st.button(
            ":material/download: 匯出我的資料",
            width="stretch",
            key="gdpr_export_btn",
        ):
            try:
                data = client.export_user_data()
                if data:
                    st.download_button(
                        label=":material/download: 下載 JSON",
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
        if st.button(
            ":material/bar_chart: 我的統計",
            width="stretch",
            key="gdpr_stats_btn",
        ):
            try:
                user_stats = client.get_user_stats()
                if user_stats:
                    st.json(user_stats)
                else:
                    st.info("尚無統計資料")
            except Exception as e:
                st.error(f"取得統計失敗: {e}")

    with col_delete:
        st.markdown("**⚠️ 危險操作**")
        confirm = st.checkbox("我確認要刪除所有個人資料", key="gdpr_delete_confirm")
        if st.button(
            ":material/delete_forever: 刪除我的資料",
            width="stretch",
            type="primary",
            disabled=not confirm,
            key="gdpr_delete_btn",
        ):
            try:
                result = client.delete_user_data(confirm=True)
                if result.get("status") == "deleted":
                    st.success("✅ 所有個人資料已永久刪除")
                else:
                    st.error(f"刪除失敗: {result.get('message', '')}")
            except Exception as e:
                st.error(f"刪除失敗: {e}")
