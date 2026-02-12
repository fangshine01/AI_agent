"""
Token 使用量追蹤中介層
記錄每個 API 請求的 Token 消耗
"""

import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class TokenTrackerMiddleware(BaseHTTPMiddleware):
    """記錄 API 請求的 Token 使用量"""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # 執行請求
        response = await call_next(request)

        # 計算處理時間
        process_time = time.time() - start_time

        # 記錄到 log
        logger.debug(
            f"[API] {request.method} {request.url.path} "
            f"- {response.status_code} "
            f"- {process_time:.3f}s"
        )

        # 在回應 header 中加入處理時間
        response.headers["X-Process-Time"] = f"{process_time:.3f}"

        return response
