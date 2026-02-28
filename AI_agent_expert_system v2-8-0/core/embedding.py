"""
Embedding — 取得文字向量嵌入
從 ai_core.py 抽離
"""

import logging
from typing import Dict, List, Tuple

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import backend.config as config
from core.llm_client import RETRYABLE_EXCEPTIONS

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
    reraise=True,
)
def get_embedding(
    text: str,
    api_key: str = None,
    base_url: str = None,
) -> Tuple[List[float], Dict]:
    """
    取得文字的 Embedding 向量

    Returns:
        (embedding_vector, usage_dict)
    """
    if not text:
        return [], {"total_tokens": 0}

    text = text.replace("\n", " ")
    if len(text) > 8000:
        text = text[:8000]

    if not api_key:
        raise ValueError("系統採用 BYOK 模式，請提供您的 API Key")

    used_base_url = base_url or config.BASE_URL

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{used_base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {api_key.strip()}",
                    "Content-Type": "application/json",
                },
                json={"input": text, "model": config.EMBEDDING_MODEL},
            )
            response.raise_for_status()

        data = response.json()
        embedding = data["data"][0]["embedding"]
        usage = data.get("usage", {"total_tokens": 0})
        return embedding, usage

    except Exception as e:
        logger.error(f"❌ Embedding API 呼叫失敗: {e}")
        raise
