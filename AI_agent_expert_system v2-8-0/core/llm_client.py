"""
LLM Client — HTTP 呼叫 Chat Completions API
從 ai_core.py 抽離的底層傳輸層
"""

import base64
import logging
import httpx
from typing import List, Dict, Optional, Tuple

import backend.config as config

logger = logging.getLogger(__name__)

# 定義可重試的例外類型（僅限暫時性錯誤）
RETRYABLE_EXCEPTIONS = (
    TimeoutError,
    ConnectionError,
    OSError,
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.ReadTimeout,
)

try:
    import openai
    RETRYABLE_EXCEPTIONS += (
        openai.RateLimitError,
        openai.APITimeoutError,
        openai.APIConnectionError,
        openai.InternalServerError,
    )
except ImportError:
    pass


def encode_image_to_base64(image_path: str) -> str:
    """將圖片編碼為 base64"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def call_chat_model(
    messages: List[Dict],
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: Optional[int] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Tuple[str, Dict]:
    """
    呼叫 Chat Completions API（標準 OpenAI 格式）

    Returns:
        (content_str, token_usage_dict)
    """
    url = base_url if base_url else config.BASE_URL
    if not url.endswith("/chat/completions"):
        url = url.rstrip("/") + "/chat/completions"

    if not api_key:
        raise ValueError("系統採用 BYOK 模式，請提供您的 API Key")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key.strip()}",
    }

    payload: Dict = {"messages": messages, "temperature": temperature}
    if model:
        payload["model"] = model
    if max_tokens:
        payload["max_tokens"] = max_tokens

    logger.debug(f"📡 API 請求: {url}")

    try:
        with httpx.Client(timeout=60.0) as client:
            logger.info(f"📤 發送請求到: {url}")
            response = client.post(url, json=payload, headers=headers)
            logger.info(f"📥 回應狀態: {response.status_code}")
            logger.debug(f"📥 回應內容: {response.text[:500] if response.text else '(空)'}")
            response.raise_for_status()
            data = response.json()

        # Token 使用
        usage = data.get("usage", {})
        token_info = {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
        }

        # 解析回應內容
        content = _extract_content(data)
        return content, token_info

    except httpx.HTTPStatusError as e:
        logger.error(f"❌ API HTTP 錯誤: {e.response.status_code} — {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"❌ API 呼叫失敗: {e}")
        raise


def _extract_content(data: Dict) -> str:
    """從 API 回應中提取文字內容（支援多種格式）"""
    if "choices" in data and len(data["choices"]) > 0:
        return data["choices"][0]["message"]["content"]
    for key in ("content", "response", "message"):
        if key in data:
            return data[key]
    logger.warning(f"⚠️ 無法解析 API 回應格式: {data}")
    return str(data)
