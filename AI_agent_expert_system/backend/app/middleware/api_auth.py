"""
API Key 驗證中介層 (可選功能)

啟用方式:
1. 在 .env 設定 SYSTEM_API_KEY=你的密鑰
2. 在 .env 設定 ENABLE_API_AUTH=true
3. 重新啟動後端

使用方式:
- 所有 API 請求需要在 Header 加上: X-API-Key: 你的密鑰
- 前端會自動從 .env 讀取並帶上
"""

import os
import logging
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# 從環境變數讀取 API Key
SYSTEM_API_KEY = os.getenv("SYSTEM_API_KEY", "")

# 白名單：不需要驗證的端點
PUBLIC_ENDPOINTS = {
    "/",
    "/health",
    "/favicon.ico",
}


class APIKeyMiddleware(BaseHTTPMiddleware):
    """API Key 驗證中介層"""

    async def dispatch(self, request: Request, call_next):
        """
        驗證每個請求的 API Key
        
        白名單端點可以直接存取
        其他端點需要提供正確的 X-API-Key header
        """
        
        # 檢查是否為白名單端點
        if request.url.path in PUBLIC_ENDPOINTS:
            return await call_next(request)
        
        # 如果沒有設定 SYSTEM_API_KEY，記錄警告但允許通過
        if not SYSTEM_API_KEY:
            logger.warning(
                f"⚠️ API Key 驗證已啟用但未設定 SYSTEM_API_KEY！"
                f"請在 .env 中設定 SYSTEM_API_KEY，"
                f"否則任何人都可以存取 API。"
            )
            return await call_next(request)
        
        # 從 Header 取得 API Key
        provided_key = request.headers.get("X-API-Key", "")
        
        # 驗證 API Key
        if provided_key != SYSTEM_API_KEY:
            client_ip = request.client.host if request.client else "unknown"
            logger.warning(
                f"🔒 未授權的 API 存取嘗試: "
                f"IP={client_ip}, "
                f"Path={request.url.path}, "
                f"Provided Key={'[空]' if not provided_key else '[無效]'}"
            )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "未授權",
                    "message": "無效的 API Key。請在 Header 中提供正確的 X-API-Key。",
                    "code": "INVALID_API_KEY"
                },
                headers={"WWW-Authenticate": "ApiKey"},
            )
        
        # API Key 正確，允許通過
        return await call_next(request)


def is_api_auth_enabled() -> bool:
    """檢查是否啟用 API Key 驗證"""
    return os.getenv("ENABLE_API_AUTH", "false").lower() == "true"


def log_auth_status():
    """記錄目前的驗證狀態"""
    if is_api_auth_enabled():
        if SYSTEM_API_KEY:
            logger.info(
                f"🔒 API Key 驗證已啟用 "
                f"(API Key 長度: {len(SYSTEM_API_KEY)} 字元)"
            )
        else:
            logger.warning(
                "⚠️ API Key 驗證已啟用但未設定 SYSTEM_API_KEY！"
                "系統將允許所有請求通過。"
            )
    else:
        logger.info(
            "🔓 API Key 驗證未啟用 "
            "(所有人都可以存取 API，僅適合內部網路使用)"
        )
