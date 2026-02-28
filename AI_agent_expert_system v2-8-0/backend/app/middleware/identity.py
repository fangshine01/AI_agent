"""
Identity Middleware - 用戶識別中介層 (v2.2.0)

採用 BYOK (Bring Your Own Key) 模式：
- 用戶的 API Key Hash 作為 user_id
- 可選 Username 欄位，避免共用 Key 時歷史混淆
- user_id = Hash(API Key) 或 Hash(API Key + Username)

使用方式:
- 前端在 Header 傳送: X-API-Key (必填), X-User-Name (選填)
- 後端自動產生 request.state.user_id
- 原始 Key 僅在呼叫 LLM 時使用，DB 僅存 Hash
"""

import hashlib
import logging
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# 不需要身份識別的端點白名單
IDENTITY_SKIP_ENDPOINTS = {
    "/",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
    "/metrics",
}


def hash_user_identity(api_key: str, username: Optional[str] = None) -> str:
    """
    產生用戶身份識別 Hash

    Args:
        api_key: 用戶的 API Key (原始值)
        username: 可選的用戶名稱 (共用 Key 時區分)

    Returns:
        str: SHA-256 Hash 前 16 字元 (足夠唯一辨識)
    """
    identity_string = api_key
    if username and username.strip():
        identity_string = f"{api_key}:{username.strip()}"

    return hashlib.sha256(identity_string.encode("utf-8")).hexdigest()[:16]


def mask_api_key(api_key: str) -> str:
    """
    遮蔽 API Key 用於日誌記錄，僅顯示前 4 碼和後 4 碼

    Args:
        api_key: 原始 API Key

    Returns:
        str: 遮蔽後的 Key (例如: sk-a****wxyz)
    """
    if not api_key or len(api_key) < 8:
        return "****"
    return f"{api_key[:4]}****{api_key[-4:]}"


class IdentityMiddleware(BaseHTTPMiddleware):
    """
    用戶識別中介層

    從 Request Header 中提取 API Key 和 Username：
    - 產生 user_id (Hash)
    - 將 user_id 和原始 Key 存入 request.state
    - 後續 Endpoint 可直接使用 request.state.user_id
    """

    async def dispatch(self, request: Request, call_next):
        # 跳過白名單端點
        path = request.url.path
        if path in IDENTITY_SKIP_ENDPOINTS or path.startswith("/files/"):
            return await call_next(request)

        # 從 Header 取得身份資訊
        api_key = request.headers.get("X-API-Key", "")
        username = request.headers.get("X-User-Name", "")

        # 產生 user_id (即使沒有 Key 也允許通過，由各 Endpoint 自行驗證)
        if api_key:
            user_id = hash_user_identity(api_key, username)
            request.state.user_id = user_id
            request.state.api_key = api_key  # 原始 Key，僅供 LLM 呼叫使用
            request.state.username = username or None
            request.state.is_authenticated = True

            logger.debug(
                f"[Identity] 用戶已識別: user_id={user_id}, "
                f"key={mask_api_key(api_key)}, "
                f"username={username or '(無)'}"
            )
        else:
            request.state.user_id = None
            request.state.api_key = None
            request.state.username = None
            request.state.is_authenticated = False

        response = await call_next(request)
        return response
