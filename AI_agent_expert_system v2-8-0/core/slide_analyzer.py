"""
Slide Analyzer — 投影片內容分析（文字/視覺模式）
從 ai_core.py 抽離
"""

import logging
from typing import List, Dict, Tuple

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import backend.config as config
from core.llm_client import (
    RETRYABLE_EXCEPTIONS,
    call_chat_model,
    encode_image_to_base64,
)

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
    reraise=True,
)
def analyze_slide(
    text: str,
    image_paths: List[str] = None,
    user_focus: str = "",
    api_mode: str = "auto",
    api_key: str = None,
    base_url: str = None,
    text_model: str = None,
    vision_model: str = None,
) -> Tuple[str, Dict]:
    """
    分析單張投影片，返回 (結構化內容, Token 使用資訊)。
    api_mode: "text_only" | "vision" | "auto"
    """
    if image_paths is None:
        image_paths = []

    use_vision = (api_mode == "vision") or (api_mode == "auto" and len(image_paths) > 0)

    if use_vision and image_paths:
        return _analyze_with_vision(
            text, image_paths, user_focus,
            api_key=api_key, base_url=base_url, model=vision_model,
        )
    return _analyze_text_only(
        text, user_focus,
        api_key=api_key, base_url=base_url, model=text_model,
    )


# ── 內部實作 ──────────────────────────────

def _analyze_text_only(
    text: str, user_focus: str = "",
    api_key: str = None, base_url: str = None, model: str = None,
) -> Tuple[str, Dict]:
    """使用純文字 API 分析"""
    _ZERO = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    if not text.strip():
        return "", _ZERO

    system_prompt = (
        "請分析以下投影片內容，提取重點資訊。\n"
        "【要求】\n"
        "1. 提取關鍵資訊並結構化輸出\n"
        "2. 保留重要數據、人名、專有名詞\n"
        "3. 若有清單或步驟，請整理成條列式\n\n"
        "請輸出結構化的知識摘要："
    )
    user_content = f"【投影片文字】\n{text}\n\n"
    if user_focus:
        user_content += f"【使用者關注點】{user_focus}"

    try:
        used_model = model or config.DEFAULT_TEXT_MODEL
        logger.debug(f"🔤 使用文字 API: {used_model}")
        result, usage = call_chat_model(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            model=used_model,
            temperature=0.3,
            api_key=api_key,
            base_url=base_url,
        )
        logger.debug(f"✅ 文字分析完成，長度: {len(result)}, Tokens: {usage['total_tokens']}")
        return result, usage
    except Exception as e:
        logger.error(f"❌ 文字 API 呼叫失敗: {e}")
        return text, _ZERO


def _analyze_with_vision(
    text: str, image_paths: List[str], user_focus: str = "",
    api_key: str = None, base_url: str = None, model: str = None,
) -> Tuple[str, Dict]:
    """使用 Vision API 分析"""
    system_prompt = (
        "請分析這張投影片，整合文字與圖片內容。\n"
        "【要求】\n"
        "1. 若有流程圖，請嘗試轉為 Mermaid Markdown 格式\n"
        "2. 若有圖表，請提取關鍵數據\n"
        "3. 整合所有資訊，輸出結構化的知識摘要\n\n"
        "請輸出結構化內容："
    )
    user_text = f"【投影片文字】\n{text if text else '(無文字)'}\n\n"
    if user_focus:
        user_text += f"【使用者關注點】{user_focus}"

    content_parts = [{"type": "text", "text": user_text}]

    for img_path in image_paths[:5]:
        try:
            img_base64 = encode_image_to_base64(img_path)
            ext = img_path.rsplit(".", 1)[-1].lower()
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/{ext};base64,{img_base64}"},
            })
        except Exception as e:
            logger.warning(f"圖片編碼失敗 {img_path}: {e}")

    try:
        used_model = model or config.DEFAULT_VISION_MODEL
        logger.debug(f"🖼️ 使用 Vision API: {used_model}, {len(image_paths)} 圖片")
        result, usage = call_chat_model(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content_parts},
            ],
            model=used_model,
            temperature=0.3,
            max_tokens=1500,
            api_key=api_key,
            base_url=base_url,
        )
        logger.debug(f"✅ Vision 分析完成，長度: {len(result)}, Tokens: {usage['total_tokens']}")
        return result, usage
    except Exception as e:
        logger.error(f"❌ Vision API 呼叫失敗: {e}")
        return _analyze_text_only(text, user_focus, api_key=api_key, base_url=base_url, model=None)
