"""
File Reader — 讀取多種格式的文件內容
從 ingestion_v3.py 抽離
"""

import os
import logging
from typing import Dict

logger = logging.getLogger(__name__)


def read_file_content(file_path: str) -> str:
    """
    讀取文件內容（支援 .txt, .md, .pptx, .pdf）

    Returns:
        str: 文件文字內容；失敗時返回空字串
    """
    ext = os.path.splitext(file_path)[1].lower()

    try:
        if ext in (".txt", ".md"):
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()

        if ext == ".pptx":
            from core import ppt_parser

            slides_data = ppt_parser.parse_ppt(file_path, extract_images=False)
            parts = []
            for slide in slides_data:
                if slide.get("text"):
                    parts.append(
                        f"--- 投影片 {slide.get('page_num', '?')} ---\n{slide['text']}"
                    )
            return "\n\n".join(parts)

        if ext == ".pdf":
            import fitz  # PyMuPDF

            doc = fitz.open(file_path)
            parts = []
            for page_num, page in enumerate(doc):
                text = page.get_text()
                if text.strip():
                    parts.append(f"--- Page {page_num + 1} ---\n{text}")
            doc.close()
            return "\n\n".join(parts)

        logger.warning(f"不支援的文件格式: {ext}")
        return ""

    except Exception as e:
        logger.error(f"讀取文件失敗: {e}")
        return ""


def extract_chapters(content: str) -> Dict[str, str]:
    """
    從內容中提取章節（以 ``---`` 或 ``# `` 為分隔）

    Returns:
        Dict[str, str]: {章節標題: 章節內容}
    """
    chapters: Dict[str, str] = {}
    current_chapter = "主要內容"
    current_content: list = []

    for line in content.split("\n"):
        if line.startswith("---") or line.startswith("# "):
            if current_content:
                chapters[current_chapter] = "\n".join(current_content)
            current_chapter = line.replace("---", "").replace("#", "").strip()
            if not current_chapter:
                current_chapter = f"章節 {len(chapters) + 1}"
            current_content = []
        else:
            current_content.append(line)

    if current_content:
        chapters[current_chapter] = "\n".join(current_content)

    if not chapters:
        chapters["完整內容"] = content

    return chapters
