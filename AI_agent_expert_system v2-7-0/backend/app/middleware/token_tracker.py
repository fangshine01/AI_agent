"""
Token 使用量追蹤中介層 (v2.2.0 增強)

功能：
- 記錄每個 API 請求的處理時間
- 多模型 Token 計算支援 (GPT / Gemini)
- Token 統計工具函式 (供其他模組使用)
"""

import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


# ========== 多模型 Token 計算 ==========

def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    """
    依據模型計算文字的 Token 數量

    Args:
        text: 輸入文字
        model: 模型 ID（如 gpt-4o-mini, gemini-2.5-flash 等）

    Returns:
        int: 估計的 Token 數量
    """
    if not text:
        return 0

    # GPT 系列：使用 tiktoken 精確計算
    if model.startswith("gpt-"):
        try:
            import tiktoken
            try:
                encoder = tiktoken.encoding_for_model(model)
            except KeyError:
                # 未知 GPT 模型，使用 cl100k_base (GPT-4 系列通用)
                encoder = tiktoken.get_encoding("cl100k_base")
            return len(encoder.encode(text))
        except ImportError:
            # 未安裝 tiktoken，使用估算
            logger.debug("[TokenTracker] tiktoken 未安裝，使用估算 (1 token ≈ 4 chars)")
            return max(1, len(text) // 4)

    # Gemini 系列：使用 BPE 估算（1 Token ≈ 4 字元）
    elif model.startswith("gemini"):
        return max(1, len(text) // 4)

    # 未知模型：保守估算（1 Token ≈ 3 字元）
    else:
        return max(1, len(text) // 3)


def estimate_image_tokens(width: int, height: int, model: str = "gpt-4o") -> int:
    """
    估算圖片的 Token 消耗

    Args:
        width: 圖片寬度 (px)
        height: 圖片高度 (px)
        model: Vision 模型

    Returns:
        int: 估計的 Token 消耗
    """
    if model.startswith("gpt-"):
        # GPT-4o Vision: 170 基底 + (寬×高 / 512)
        return 170 + (width * height // 512)
    elif model.startswith("gemini"):
        # Gemini: 依解析度分級
        total_pixels = width * height
        if total_pixels <= 256 * 256:
            return 258  # 小圖
        elif total_pixels <= 768 * 768:
            return 516  # 中圖
        else:
            return 1032  # 大圖
    return 500  # 預設估算


class TokenTrackerMiddleware(BaseHTTPMiddleware):
    """記錄 API 請求的處理時間與 Token 使用量"""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # 執行請求
        response = await call_next(request)

        # 計算處理時間
        process_time = time.time() - start_time

        # 取得 user_id（由 IdentityMiddleware 設定）
        user_id = getattr(request.state, "user_id", "anonymous")

        # 記錄到 log（僅記錄 API 呼叫，跳過靜態資源）
        path = request.url.path
        if path.startswith("/api/"):
            logger.info(
                f"[API] {request.method} {path} | "
                f"user={user_id} | "
                f"status={response.status_code} | "
                f"time={process_time:.3f}s"
            )

        # 在回應 header 中加入處理時間
        response.headers["X-Process-Time"] = f"{process_time:.3f}"

        return response
