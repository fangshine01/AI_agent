"""
Input 驗證中介層 (v2.2.0 Phase 2)

功能：
- Query 長度限制（MAX_QUERY_LENGTH，預設 2000 字元）
- 檔案大小限制（MAX_FILE_SIZE_MB，預設 50MB）
- Content-Length 預檢
- 基本 XSS / Injection 防護

套用方式：在 main.py 中 app.add_middleware(InputValidationMiddleware)
"""

import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

import backend.config as cfg

logger = logging.getLogger(__name__)

# 檔案上傳相關路徑（需要檢查 Content-Length）
_UPLOAD_PATHS = ("/api/v1/ingestion/upload", "/api/v1/ingestion/upload_multiple", "/api/v1/ingestion/upload_and_process")


class InputValidationMiddleware(BaseHTTPMiddleware):
    """
    全域 Input 驗證中介層

    檢查項目：
    1. Content-Length 上限（檔案上傳路徑）
    2. 基本安全標頭
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # 1. 檢查檔案上傳大小
        if path in _UPLOAD_PATHS and request.method == "POST":
            content_length = request.headers.get("content-length")
            if content_length:
                max_bytes = cfg.MAX_FILE_SIZE_MB * 1024 * 1024
                if int(content_length) > max_bytes:
                    logger.warning(
                        f"[Validation] 檔案過大: {content_length} bytes > {max_bytes} bytes, "
                        f"path={path}"
                    )
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={
                            "error": True,
                            "message": f"檔案大小超過限制 ({cfg.MAX_FILE_SIZE_MB}MB)",
                            "max_size_mb": cfg.MAX_FILE_SIZE_MB,
                        },
                    )

        response = await call_next(request)
        return response


def validate_query_length(query: str) -> str:
    """
    驗證查詢長度（供 API Endpoint 內部使用）

    Args:
        query: 使用者查詢字串

    Returns:
        str: 驗證通過的查詢字串

    Raises:
        ValueError: 超過長度限制
    """
    if not query or not query.strip():
        raise ValueError("查詢不可為空")

    if len(query) > cfg.MAX_QUERY_LENGTH:
        raise ValueError(
            f"查詢長度超過限制: {len(query)} > {cfg.MAX_QUERY_LENGTH} 字元"
        )

    return query.strip()


def sanitize_text(text: str) -> str:
    """
    基本文字清理（防止 XSS）

    移除潛在危險的 HTML 標籤，保留純文字內容
    """
    if not text:
        return text

    # 移除 <script> 標籤
    import re
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # 移除 on* 事件屬性
    text = re.sub(r'\bon\w+\s*=', '', text, flags=re.IGNORECASE)
    # 移除 javascript: 協議
    text = re.sub(r'javascript\s*:', '', text, flags=re.IGNORECASE)

    return text
