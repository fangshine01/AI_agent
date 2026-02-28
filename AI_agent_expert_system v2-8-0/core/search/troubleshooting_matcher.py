# -*- coding: utf-8 -*-
"""
Troubleshooting 精準匹配模組

從查詢中提取產品/defect code 並嘗試精準匹配 troubleshooting_metadata
"""

import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)


def try_exact_troubleshooting_match(query: str, filters: Optional[Dict] = None) -> Optional[Dict]:
    """
    嘗試精準匹配 Troubleshooting 文件 (v5.0)

    條件:
    1. filters 中有明確的 product 和 defect_code
    2. 或從 query 中可以解析出產品和 Defect Code

    Returns:
        Dict: 精準匹配結果 (含完整 8D 報告), 或 None
    """
    try:
        from core.database.metadata_ops import search_troubleshooting
        from core.database.vector_ops import get_chunks_by_doc_id
        from core.database.keyword_ops import search_by_keywords

        product = None
        defect_code = None

        # 方法 1: 從 filters 取得
        if filters:
            product = filters.get('product') or filters.get('product_model')
            defect_code = filters.get('defect_code')

        # 方法 2: 從 query 中提取 (使用 keyword_mappings)
        if not (product and defect_code):
            extracted = _extract_ts_keywords_from_query(query)
            if not product and extracted.get('product'):
                product = extracted['product']
            if not defect_code and extracted.get('defect_code'):
                defect_code = extracted['defect_code']

        if not (product or defect_code):
            return None

        logger.info(f"嘗試 Troubleshooting 精準匹配: product={product}, defect_code={defect_code}")

        # 從 troubleshooting_metadata 表精準查詢
        ts_results = search_troubleshooting(
            product_model=product,
            defect_code=defect_code
        )

        if not ts_results:
            # Fallback: 嘗試從 document_keywords 表搜尋
            kw_filters = {}
            if product:
                kw_filters['產品'] = product
            if defect_code:
                kw_filters['Defect Code'] = defect_code

            doc_ids = search_by_keywords(kw_filters)
            if not doc_ids:
                logger.info("精準匹配無結果,降級到向量搜尋")
                return None

            # 取第一個匹配的 doc
            from core.database.document_ops import get_document
            doc = get_document(doc_ids[0])
            if not doc:
                return None

            ts_results = [{
                'doc_id': doc_ids[0],
                'filename': doc.get('filename'),
                'doc_type': 'Troubleshooting',
                'product_model': product,
                'defect_code': defect_code
            }]

        # 取得第一個匹配文件的完整 chunks
        matched = ts_results[0]
        doc_id = matched['doc_id']
        chunks = get_chunks_by_doc_id(doc_id)

        if not chunks:
            return None

        # 組裝結果 (相容現有 chat_app 顯示邏輯)
        formatted_chunks = []
        full_content = ""
        for chunk in chunks:
            formatted_chunks.append({
                'chunk_id': chunk.get('chunk_id'),
                'title': chunk.get('source_title', '未命名'),
                'content': chunk.get('content', chunk.get('text_content', '')),
                'similarity': 1.0
            })
            full_content += chunk.get('content', chunk.get('text_content', '')) + "\n\n"

        result = {
            'doc_id': doc_id,
            'file_name': matched.get('filename', 'Unknown'),
            'file_type': 'Troubleshooting',
            'product_model': matched.get('product_model'),
            'defect_code': matched.get('defect_code'),
            'station': matched.get('station'),
            'yield_loss': matched.get('yield_loss'),
            'chunks': formatted_chunks,
            'raw_content': full_content.strip(),
            'content': full_content.strip(),
            'total_score': 1.0,
            'similarity': 1.0,
            'exact_match': True
        }

        logger.info(f"✅ Troubleshooting 精準匹配成功: {matched.get('filename')}")
        return result

    except Exception as e:
        logger.warning(f"Troubleshooting 精準匹配失敗: {e}")
        return None


def _extract_ts_keywords_from_query(query: str) -> Dict:
    """
    從查詢字串中提取產品型號和 Defect Code

    使用 keyword_mappings 進行匹配
    """
    try:
        from core.keyword_manager import get_keyword_manager

        km = get_keyword_manager()
        all_data = km.get_all_data()

        extracted = {}
        query_lower = query.lower()

        # 匹配產品
        products = all_data.get('產品', [])
        for product in products:
            if product.lower() in query_lower:
                extracted['product'] = product
                break

        # 匹配 Defect Code
        defect_codes = all_data.get('Defect Code', [])
        for code in defect_codes:
            if code.lower() in query_lower:
                extracted['defect_code'] = code
                break

        # 匹配站點
        stations = all_data.get('站點', [])
        for station in stations:
            if station.lower() in query_lower:
                extracted['station'] = station
                break

        return extracted

    except Exception as e:
        logger.warning(f"提取 TS 關鍵字失敗: {e}")
        return {}
