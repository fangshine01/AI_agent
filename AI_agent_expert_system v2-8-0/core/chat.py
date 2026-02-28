"""
Chat — RAG 問答回應
從 ai_core.py 抽離
"""

import logging
from typing import Dict, List, Tuple

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
def chat_response(
    question: str,
    context_slides: List[Dict],
    conversation_history: List[Dict] = None,
    api_key: str = None,
    base_url: str = None,
) -> Tuple[str, Dict]:
    """
    基於檢索到的內容回答使用者問題

    Returns:
        (answer_text, usage_dict)
    """
    if conversation_history is None:
        conversation_history = []

    if context_slides:
        system_prompt, user_prompt = _build_rag_prompt(question, context_slides)
    else:
        system_prompt, user_prompt = _build_fallback_prompt(question)

    try:
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history[-10:])
        messages.append({"role": "user", "content": user_prompt})

        logger.debug(f"💬 問答 API 呼叫: {question[:50]}...")
        answer, usage = call_chat_model(
            messages=messages,
            model=config.DEFAULT_TEXT_MODEL,
            temperature=0.5,
            api_key=api_key,
            base_url=base_url,
        )
        logger.debug(f"✅ 問答完成，Tokens: {usage['total_tokens']}")
        return answer, usage

    except Exception as e:
        logger.error(f"❌ 問答 API 呼叫失敗: {e}")
        return f"抱歉，發生錯誤:{str(e)}", {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }


# ── Prompt 構建 ──────────────────────────────

def _build_rag_prompt(question: str, context_slides: List[Dict]):
    """有上下文資料時的 Prompt"""
    context_text = "\n\n".join(
        f"【來源：{s['file_name']} - 第 {s['page_num']} 頁】\n{s['content']}"
        for s in context_slides
    )
    system = (
        "請根據 User 提供的參考資料進行統整與總結。"
        "你的任務是化繁為簡，並在回答最後主動提供額外的延伸補充與行動建議。"
        "若參考資料不足以回答問題，請明確告知。"
    )
    user = f"【上下文資料】\n{context_text}\n\n【使用者問題】\n{question}\n\n請根據上述上下文回答問題："
    return system, user


def _build_fallback_prompt(question: str):
    """無上下文時的 Prompt"""
    system = (
        "因為知識庫中沒有相關資料，請直接根據你的內建知識與網路搜尋能力回答 User 的問題。"
        "請確保答案正確且細節豐富，並適當區分段落，讓閱讀體驗順暢。"
        "回答結束時一樣給予延伸補充或行動建議。"
    )
    return system, question
