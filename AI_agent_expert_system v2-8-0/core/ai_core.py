"""
AI Expert System - AI Core Facade (v2.7.0)
統一的公開介面 — 所有呼叫者只需 ``from core import ai_core``。
實作已拆分到:
  - core.llm_client        (call_chat_model, encode_image_to_base64)
  - core.slide_analyzer     (analyze_slide)
  - core.embedding          (get_embedding)
  - core.chat               (chat_response)
  - core.keyword_extractor  (extract_keywords)
"""

# Re-export public API so existing callers don't break
from core.llm_client import call_chat_model, encode_image_to_base64  # noqa: F401
from core.slide_analyzer import analyze_slide                        # noqa: F401
from core.embedding import get_embedding                             # noqa: F401
from core.chat import chat_response                                  # noqa: F401
from core.keyword_extractor import extract_keywords                  # noqa: F401

__all__ = [
    "call_chat_model",
    "encode_image_to_base64",
    "analyze_slide",
    "get_embedding",
    "chat_response",
    "extract_keywords",
]
