"""
Image Ingestion — Gemini Vision 圖片處理流程
從 ingestion_v3.py 的 _process_image_with_gemini 抽離
"""

import os
import logging
import tempfile
from pathlib import Path
from typing import Callable, Dict, Optional

from core import database

logger = logging.getLogger(__name__)


def process_image_with_gemini(
    file_path: str,
    doc_type: str,
    progress_callback: Optional[Callable] = None,
    parent_doc_id: int = None,
) -> Dict:
    """
    使用 Gemini Vision 將圖片轉為 Markdown 並入庫。

    Returns:
        Dict: {'success': bool, 'doc_id': int, 'chunks': int, 'message': str}
    """
    filename = os.path.basename(file_path)

    try:
        if progress_callback:
            progress_callback(f"🖼️ Gemini 正在辨識圖片: {filename}")

        logger.info(f"🖼️ 開始 Gemini 圖片處理: {filename}")

        from backend.app.core.image_processor import get_image_processor

        processor = get_image_processor()
        markdown_content = processor.process_image(file_path, prompt_type="auto")

        if not markdown_content:
            return {"success": False, "message": f"Gemini 回傳空內容: {filename}"}

        # Token 追蹤（估算）
        try:
            est = len(markdown_content) // 4
            database.log_token_usage(
                file_name=filename,
                operation="gemini_vision",
                usage={
                    "prompt_tokens": est,
                    "completion_tokens": est,
                    "total_tokens": est * 2,
                },
            )
        except Exception as e:
            logger.warning(f"⚠️ Gemini Token 追蹤失敗: {e}")

        logger.info(
            f"✅ Gemini 圖片辨識完成: {filename} ({len(markdown_content)} chars)"
        )

        # 儲存至暫存 MD → 走標準入庫流程
        if progress_callback:
            progress_callback(f"📝 正在將 Gemini 結果入庫: {filename}")

        md_filename = Path(file_path).stem + "_gemini.md"
        md_temp_path = os.path.join(tempfile.gettempdir(), md_filename)
        with open(md_temp_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        # 延遲匯入避免循環
        from core.ingestion_v3 import process_document_v3

        result = process_document_v3(
            file_path=md_temp_path,
            doc_type=doc_type,
            analysis_mode="text_only",
            enable_gemini_vision=False,
            parent_doc_id=parent_doc_id,
            progress_callback=progress_callback,
        )

        try:
            os.remove(md_temp_path)
        except OSError:
            pass

        if result.get("success"):
            logger.info(
                f"✅ 圖片入庫完成: {filename} → doc_id={result.get('doc_id')}, "
                f"chunks={result.get('chunks')}"
            )

        return result

    except ImportError:
        logger.warning(f"⚠️ Gemini 模組未安裝，無法處理圖片: {filename}")
        return {
            "success": False,
            "message": f"Gemini 模組未安裝 (pip install google-generativeai): {filename}",
        }
    except Exception as e:
        logger.error(f"❌ Gemini 圖片處理失敗: {filename} - {e}")
        return {"success": False, "message": f"Gemini 處理失敗: {str(e)}"}
