"""
Rate Limiting 中介層 (v2.2.0)

基於 slowapi 實現的用戶級速率限制：
- 每分鐘 30 次請求 (預設)
- 每小時 500 次請求 (預設)
- 管理員端點: 每分鐘 100 次
- 以 user_id (BYOK Hash) 作為限流 key

配置來源: backend/config.py (可透過 .env 覆寫)
"""

import logging
from typing import Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

import backend.config as cfg

logger = logging.getLogger(__name__)


def _get_user_key(request: Request) -> str:
    """
    取得速率限制的 key

    優先使用 BYOK user_id（由 IdentityMiddleware 設定），
    若未認證則 fallback 到 IP 地址。
    """
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    return f"ip:{get_remote_address(request)}"


# 建立全域 limiter 實例
limiter = Limiter(key_func=_get_user_key)

# 預設速率限制字串
DEFAULT_RATE_LIMIT = f"{cfg.RATE_LIMIT_PER_MINUTE}/minute"
HOURLY_RATE_LIMIT = f"{cfg.RATE_LIMIT_PER_HOUR}/hour"
ADMIN_RATE_LIMIT = f"{cfg.ADMIN_RATE_LIMIT_PER_MINUTE}/minute"


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    速率超限時的錯誤回應

    回傳 429 Too Many Requests，包含：
    - Retry-After header
    - 結構化錯誤訊息
    """
    retry_after = exc.detail.split("per")[0].strip() if exc.detail else "稍後"
    logger.warning(
        f"[RateLimit] 超限: key={_get_user_key(request)} | "
        f"path={request.url.path} | detail={exc.detail}"
    )

    return JSONResponse(
        status_code=429,
        content={
            "error": True,
            "status_code": 429,
            "message": "請求過於頻繁，請稍後再試",
            "detail": f"速率限制: {exc.detail}",
        },
        headers={"Retry-After": "60"},
    )


def setup_rate_limiter(app):
    """
    將 Rate Limiter 安裝到 FastAPI app

    使用方式 (在 main.py 中):
        from backend.app.middleware.rate_limiter import setup_rate_limiter, limiter
        app.state.limiter = limiter
        setup_rate_limiter(app)

    在路由中使用 (裝飾器方式):
        from backend.app.middleware.rate_limiter import limiter, DEFAULT_RATE_LIMIT

        @router.post("/query")
        @limiter.limit(DEFAULT_RATE_LIMIT)
        async def query(request: Request, ...):
            ...
    """
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    logger.info(
        f"⏱️ Rate Limiter 已啟用: {DEFAULT_RATE_LIMIT}, {HOURLY_RATE_LIMIT}"
    )
