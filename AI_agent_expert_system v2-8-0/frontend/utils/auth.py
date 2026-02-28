"""
Admin 登入驗證邏輯

使用 SHA-256 hash 比對管理員帳密（從 .env 讀取）
環境變數:
    ADMIN_USERNAME: 管理員帳號（預設 admin）
    ADMIN_PASSWORD_HASH: 密碼的 SHA-256 hex 值

密碼 hash 生成方式:
    python -c "import hashlib; print(hashlib.sha256('YourPassword'.encode()).hexdigest())"
"""

import os
import hashlib
import hmac
import streamlit as st


def verify_admin_credentials(username: str, password: str) -> bool:
    """
    比對管理員帳密

    Returns:
        True 若帳密正確
    """
    expected_user = os.getenv("ADMIN_USERNAME", "admin")
    expected_hash = os.getenv("ADMIN_PASSWORD_HASH", "")

    if not expected_hash:
        # 若未設定 hash，預設密碼為 "admin"（開發環境用）
        expected_hash = hashlib.sha256("admin".encode()).hexdigest()

    actual_hash = hashlib.sha256(password.encode()).hexdigest()
    return username == expected_user and hmac.compare_digest(actual_hash, expected_hash)


def is_admin_logged_in() -> bool:
    """檢查是否已登入"""
    return st.session_state.get("admin_logged_in", False)


def admin_logout():
    """登出"""
    st.session_state.admin_logged_in = False
