"""
Base API Client — 共用 HTTP 請求與 BYOK 身份管理

所有領域客戶端（Chat / Admin / Search）的基底類別。
負責：
- 通用 HTTP 請求方法（自動附加 BYOK 標頭）
- BYOK 身份資訊管理
- 健康檢查

依 organizing-streamlit-code skill：
  將業務邏輯從超大 api_client.py 拆出，各自聚焦單一職責。
"""

import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 60.0


class BaseClient:
    """
    FastAPI 後端 API 基底客戶端

    支援 BYOK 身份識別：
    - 透過 X-API-Key 和 X-User-Name 標頭傳送身份資訊
    - 後端 IdentityMiddleware 會根據這些標頭產生 user_id
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.api_url = f"{self.base_url}/api/v1"

        # 系統級 API Key（舊有，用於 API Auth 中介層）
        self._system_api_key = os.getenv("SYSTEM_API_KEY", "")

        # BYOK 身份資訊（由使用者在前端設定）
        self._user_api_key: Optional[str] = None
        self._user_name: Optional[str] = None
        self._provider: Optional[str] = None  # "openai" | "gemini"

    # ========== BYOK 身份管理 ==========

    def set_user_identity(self, api_key: str, username: str = ""):
        """設定 BYOK 使用者身份"""
        self._user_api_key = api_key
        self._user_name = username
        self._provider = "openai"
        logger.info(f"[BaseClient] BYOK 身份已設定: username={username or '(無)'}")

    def clear_user_identity(self):
        """清除 BYOK 身份資訊"""
        self._user_api_key = None
        self._user_name = None
        self._provider = None
        logger.info("[BaseClient] BYOK 身份已清除")

    @property
    def is_authenticated(self) -> bool:
        """是否已設定 BYOK 身份"""
        return self._user_api_key is not None

    def _build_headers(self) -> dict:
        """建構請求標頭（含 BYOK + 系統級 API Key）"""
        headers = {}
        if self._user_api_key:
            headers["X-API-Key"] = self._user_api_key
        if self._user_name:
            headers["X-User-Name"] = self._user_name
        if self._system_api_key and "X-API-Key" not in headers:
            headers["X-API-Key"] = self._system_api_key
        return headers

    # ========== 通用請求方法 ==========

    def _request(self, method: str, path: str, **kwargs) -> dict:
        """通用 HTTP 請求方法，自動附加 BYOK 標頭"""
        try:
            url = f"{self.base_url}{path}" if path.startswith("/") else f"{self.api_url}/{path}"
            headers = kwargs.get("headers", {})
            headers.update(self._build_headers())
            kwargs["headers"] = headers
            with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
                resp = client.request(method, url, **kwargs)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error(f"API 請求失敗 [{method} {path}]: {e}")
            return {"status": "error", "message": str(e)}

    # ========== Health ==========

    def health_check(self) -> dict:
        """健康檢查"""
        try:
            headers = self._build_headers()
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(f"{self.base_url}/health", headers=headers)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error(f"健康檢查失敗: {e}")
            return {"status": "unhealthy", "error": str(e)}
