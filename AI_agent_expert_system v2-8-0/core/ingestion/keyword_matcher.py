"""
Keyword Matcher — 從文件內容匹配關鍵字並儲存
從 ingestion_v3.py 的 _save_keywords_to_db 抽離
"""

import logging
from typing import Dict

from core import database

logger = logging.getLogger(__name__)


def save_keywords_to_db(
    doc_id: int,
    raw_content: str,
    doc_type: str,
    metadata: Dict,
) -> None:
    """
    從文件內容中提取關鍵字並儲存到 document_keywords 表。

    方法 1: 文字比對 keyword_mappings
    方法 2: 從 AI 元數據補充欄位
    """
    from core.keyword_manager import get_keyword_manager

    km = get_keyword_manager()
    all_mappings = km.get_all_data()

    matched: Dict[str, list] = {}

    # 方法 1: keyword_mappings 文字比對
    content_lower = raw_content.lower() if raw_content else ""
    for category, keyword_list in all_mappings.items():
        for keyword in keyword_list:
            if keyword.lower() in content_lower:
                matched.setdefault(category, [])
                if keyword not in matched[category]:
                    matched[category].append(keyword)

    # 方法 2: AI 元數據補充
    _META_MAP = {
        "product_model": "產品",
        "defect_code": "Defect Code",
        "station": "站點",
        "factory": "廠別",
    }
    for meta_key, category in _META_MAP.items():
        value = metadata.get(meta_key)
        if value:
            matched.setdefault(category, [])
            if value not in matched[category]:
                matched[category].append(value)

    if matched:
        database.save_document_keywords(doc_id, matched, source="ai", confidence=0.9)
        logger.info(f"✓ 關鍵字已儲存 (doc_id: {doc_id}): {matched}")
    else:
        logger.info(f"⚠️ 未匹配到關鍵字 (doc_id: {doc_id})")
