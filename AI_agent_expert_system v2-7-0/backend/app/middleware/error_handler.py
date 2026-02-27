"""
全域錯誤處理中介層 (v2.2.0)

功能：
- 攔截所有未處理例外，回傳統一 JSON 格式
- 為每個錯誤產生唯一 error_id 方便追蹤
- 記錄結構化錯誤日誌（含 traceback）
- 區分開發 / 正式環境的回傳細節

統一錯誤回應格式：
{
    "error": true,
    "error_id": "abc12345",
    "status_code": 500,
    "message": "伺服器內部錯誤",
    "detail": "...(僅開發環境)"
}
"""

import uuid
import logging
import traceback
from datetime import datetime

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    全域例外處理中介層

    捕捉所有未處理的例外（不含 HTTPException，FastAPI 已自行處理），
    回傳統一格式的 JSON 錯誤回應。
    """

    def __init__(self, app, debug: bool = False):
        super().__init__(app)
        self.debug = debug

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response

        except Exception as exc:
            error_id = uuid.uuid4().hex[:8]
            timestamp = datetime.utcnow().isoformat()

            # 結構化日誌
            logger.error(
                f"[ErrorHandler] error_id={error_id} | "
                f"method={request.method} path={request.url.path} | "
                f"exception={type(exc).__name__}: {exc}",
                exc_info=True,
            )

            # 建構回應 body
            body = {
                "error": True,
                "error_id": error_id,
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "伺服器內部錯誤，請稍後再試",
                "timestamp": timestamp,
            }

            # 開發環境才附加詳細資訊
            if self.debug:
                body["detail"] = str(exc)
                body["traceback"] = traceback.format_exc()

            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=body,
            )
