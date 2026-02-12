"""
Gemini Vision API 整合 - 圖片轉 Markdown
支援表格、流程圖、架構圖自動辨識與轉換
"""

import os
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class GeminiImageProcessor:
    """Gemini 圖片處理器"""

    def __init__(self, model_name: str = "gemini-2.0-flash-exp"):
        try:
            import google.generativeai as genai

            api_key = os.getenv("GEMINI_API_KEY", "")
            if not api_key:
                raise ValueError("GEMINI_API_KEY 未設定")

            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(model_name)
            self._genai = genai
            logger.info(f"✅ Gemini 處理器初始化成功: {model_name}")
        except ImportError:
            raise ImportError("請安裝 google-generativeai: pip install google-generativeai")

    def process_image(self, image_path: str, prompt_type: str = "auto") -> Optional[str]:
        """
        處理圖片並生成 Markdown

        Args:
            image_path: 圖片路徑
            prompt_type: 'table', 'flowchart', 'diagram', 'auto'

        Returns:
            str: Markdown 格式內容
        """
        try:
            img = Path(image_path)
            if not img.exists():
                raise FileNotFoundError(f"圖片不存在: {image_path}")

            # 取得 MIME type
            ext = img.suffix.lower()
            mime_map = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".gif": "image/gif",
                ".webp": "image/webp",
            }
            mime_type = mime_map.get(ext, f"image/{ext[1:]}")

            # 根據類型選擇 Prompt
            prompt = self._get_prompt(prompt_type)

            # 呼叫 Gemini Vision API
            response = self.model.generate_content(
                [prompt, {"mime_type": mime_type, "data": img.read_bytes()}]
            )

            markdown_content = response.text
            logger.info(f"✅ Gemini 圖片處理成功: {img.name} ({len(markdown_content)} chars)")

            return markdown_content

        except Exception as e:
            logger.error(f"❌ Gemini 圖片處理失敗: {e}")
            return None

    def _get_prompt(self, prompt_type: str) -> str:
        """取得對應的 Prompt"""
        prompts = {
            "table": """請將此圖片中的表格精確轉換為 Markdown 格式。
要求：
1. 完整保留所有儲存格內容
2. 正確對齊欄位
3. 使用標準 Markdown 語法
4. 若有合併儲存格，請在備註說明""",
            "flowchart": """請將此流程圖轉換為 Mermaid 語法。
要求：
1. 識別所有節點和連接關係
2. 使用 `graph TD` 或 `flowchart TD` 格式
3. 節點文字使用繁體中文
4. 保持原圖的邏輯結構""",
            "diagram": """請詳細描述此圖表的內容，並以 Markdown 格式標註重點資訊。
包含：
1. 圖表類型 (架構圖/關係圖/示意圖)
2. 主要元素說明
3. 關鍵連接關係
4. 若可能，轉為 Mermaid 或表格""",
            "auto": """請分析這張圖片的內容類型 (表格/流程圖/架構圖/其他)，並轉換為最適合的 Markdown 格式。
- 若為表格 → Markdown table
- 若為流程圖 → Mermaid flowchart
- 若為架構圖 → Mermaid diagram 或詳細文字說明
- 其他 → 結構化文字描述

請用繁體中文回答。""",
        }
        return prompts.get(prompt_type, prompts["auto"])


# 全域單例
_processor: Optional[GeminiImageProcessor] = None


def get_image_processor() -> GeminiImageProcessor:
    """取得 Gemini 處理器單例"""
    global _processor
    if _processor is None:
        _processor = GeminiImageProcessor()
    return _processor
