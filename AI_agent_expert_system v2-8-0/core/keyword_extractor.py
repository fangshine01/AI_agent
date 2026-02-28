"""
Keyword Extractor — 從文件文字提取關鍵字
從 ai_core.py 抽離
"""

import logging
from typing import List

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import backend.config as config
from core.llm_client import RETRYABLE_EXCEPTIONS, call_chat_model

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
    reraise=True,
)
def extract_keywords(
    text: str,
    api_key: str = None,
    base_url: str = None,
) -> List[str]:
    """
    從文字中提取 3-5 個關鍵字

    Returns:
        List[str]: 關鍵字列表
    """
    if not text or len(text) < 10:
        return []

    system_prompt = (
        "請從技術文件中提取 3-5 個關鍵字。\n"
        "【要求】\n"
        "1. 專注於：產品型號(如 N706)、機台站點(如 Station A)、Defect Code(如 E001)、專有名詞\n"
        "2. 只輸出關鍵字，用逗號分隔\n"
        "3. 不要輸出任何解釋文字"
    )
    user_content = f"【文件內容】\n{text[:2000]}... (下略)\n\n關鍵字："

    try:
        result, _ = call_chat_model(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            model=config.DEFAULT_TEXT_MODEL,
            temperature=0.3,
            max_tokens=100,
            api_key=api_key,
            base_url=base_url,
        )
        if result:
            return [k.strip() for k in result.replace("、", ",").split(",") if k.strip()]
        return []
    except Exception as e:
        logger.error(f"❌ 關鍵字提取失敗: {e}")
        return []
