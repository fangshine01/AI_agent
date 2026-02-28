"""
AI Expert System - Admin Login Page
Admin App 專用登入頁面

依 building-streamlit-multipage-apps skill：
- 條件式導覽：登入成功後 st.rerun() 切換到 Admin 頁面
- 使用 st.form 包裝，按下 Enter 或按鈕才提交
"""

import streamlit as st
from utils.auth import verify_admin_credentials


st.markdown(
    "<div style='max-width: 420px; margin: 4rem auto;'>",
    unsafe_allow_html=True,
)

with st.container(border=True):
    st.markdown("### :material/lock: 管理員登入")
    st.caption("請輸入管理員帳號與密碼")

    with st.form("admin_login_form"):
        username = st.text_input("帳號", placeholder="admin")
        password = st.text_input("密碼", type="password")
        submitted = st.form_submit_button(
            ":material/login: 登入",
            width="stretch",
        )

    if submitted:
        if not username or not password:
            st.error("請輸入帳號與密碼")
        elif verify_admin_credentials(username, password):
            st.session_state.admin_logged_in = True
            st.rerun()
        else:
            st.error("❌ 帳號或密碼錯誤")

st.markdown("</div>", unsafe_allow_html=True)

st.divider()
st.caption(":material/lock: Admin App | 密碼由系統管理員透過 ADMIN_PASSWORD_HASH 環境變數設定")
