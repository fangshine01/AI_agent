# -*- coding: utf-8 -*-
"""
搜尋結果後處理模組

去重、標準化、文件分組、信心度計算、交叉查詢檢測
"""

import logging
from typing import List, Dict

from .intent_analyzer import QueryIntent

logger = logging.getLogger(__name__)


def post_process_results(
    results: List[Dict],
    query: str,
    intent: QueryIntent,
    enable_grouping: bool = True,
    mode: str = 'qa',
    query_type: str = 'general'
) -> List[Dict]:
    """
    後處理結果

    - 去重
    - 文件分組 (新增)
    - 補充上下文
    - 調整排序

    Args:
        results: 搜尋結果
        query: 查詢字串
        intent: 查詢意圖
        enable_grouping: 是否啟用文件分組
        mode: 'training' 或 'qa'
        query_type: 查詢類型 ('troubleshooting', 'procedure', 'general' 等)
    """
    # 1. 根據 chunk_id 去重並標準化
    seen_chunks = set()
    deduped_results = []

    for result in results:
        # --- 標準化開始 ---
        # 確保 file_name 存在
        if 'file_name' not in result:
            # 嘗試從 document 字典中獲取
            doc_info = result.get('document', {})
            if isinstance(doc_info, dict):
                result['file_name'] = doc_info.get('filename') or doc_info.get('file_name')

            # 若仍無, 嘗試從 filename 獲取
            if not result.get('file_name'):
                result['file_name'] = result.get('filename', 'Unknown Document')

        # 確保 raw_content 存在
        if 'raw_content' not in result or not result['raw_content']:
            # 優先順序: content > text_content > preview
            result['raw_content'] = result.get('content') or result.get('text_content') or result.get('preview', '')

            # Fallback: 若仍為空且有 chunk_id, 嘗試從 DB 重新讀取
            if not result['raw_content'] and result.get('chunk_id'):
                try:
                    from core.database.vector_ops import get_chunk_content
                    content = get_chunk_content(result['chunk_id'])
                    if content:
                        result['raw_content'] = content
                        result['content'] = content  # 同步更新 content
                        logger.info(f"✓ 從 DB 補回內容 (Chunk ID: {result['chunk_id']}, Length: {len(content)})")
                    else:
                        logger.warning(f"✗ 無法從 DB 讀取內容 (Chunk ID: {result['chunk_id']})")
                except Exception as e:
                    logger.error(f"✗ 讀取內容時發生錯誤: {e}")

        # 確保 author 存在
        if 'author' not in result:
            result['author'] = result.get('document', {}).get('author', 'System')

        # 確保 file_type 存在
        if 'file_type' not in result:
             result['file_type'] = result.get('document', {}).get('doc_type', 'Unknown')
        # --- 標準化結束 ---

        chunk_id = result.get('chunk_id')
        if chunk_id:
            if chunk_id not in seen_chunks:
                seen_chunks.add(chunk_id)
                deduped_results.append(result)
        else:
            # 如果沒有 chunk_id (例如檔名搜尋),保留
            deduped_results.append(result)

    # 2. 文件分組 (新增功能)
    if enable_grouping:
        try:
            from .document_grouping import (
                group_chunks_by_document,
                format_grouped_results
            )
            import backend.config as config

            grouping_config = getattr(config, 'DOCUMENT_GROUPING', {
                'enabled': True,
                'similarity_thresholds': {'qa': 0.60, 'training': 0.50},
                'token_budget': {'qa': 6000, 'training': 8000},
                'use_db_summary_directly': True
            })

            # 針對 Troubleshooting 使用超大 token budget 以確保取得所有 chunks
            if query_type == 'troubleshooting':
                token_budget = 999999  # 超大預算，確保不會被截斷
                logger.info("Troubleshooting 模式: 使用無限 token budget 以取得所有 chunks")
            else:
                token_budget = grouping_config['token_budget'].get(mode)

            # 執行分組
            grouped = group_chunks_by_document(
                chunks=deduped_results,
                mode=mode,
                similarity_thresholds=grouping_config['similarity_thresholds'],
                token_budget=token_budget
            )

            # 格式化為結果列表
            deduped_results = format_grouped_results(
                grouped,
                include_summary=grouping_config['use_db_summary_directly']
            )

            logger.info(f"✅ 文件分組完成: {len(grouped)} 個文件")

        except Exception as e:
            logger.warning(f"文件分組失敗,使用原始結果: {e}")

    # 3. 根據意圖調整排序
    if intent == QueryIntent.TROUBLESHOOTING:
        # 優先顯示 Troubleshooting 類型的文件
        deduped_results.sort(
            key=lambda x: (
                x.get('file_type') == 'Troubleshooting' or x.get('doc_type') == 'Troubleshooting',
                x.get('total_score', x.get('similarity', x.get('match_score', x.get('avg_similarity', 0))))
            ),
            reverse=True
        )

    return deduped_results


def calculate_confidence(results: List[Dict]) -> float:
    """計算結果信心度"""
    if not results:
        return 0.0

    # 基於最高分與平均分的差異
    scores = []
    for r in results:
        score = r.get('total_score', r.get('similarity', r.get('match_score', 0)))
        if score:
            scores.append(score)

    if not scores:
        return 0.0

    max_score = max(scores)
    avg_score = sum(scores) / len(scores)

    # 如果最高分明顯高於平均,信心度較高
    confidence = max_score if max_score > avg_score * 1.5 else avg_score
    return min(confidence, 1.0)


def is_cross_query(results: List[Dict]) -> bool:
    """
    檢測是否為交叉查詢(多個文件)

    Args:
        results: 搜尋結果列表

    Returns:
        bool: True 表示結果包含多個不同文件, False 表示單一文件或無結果
    """
    if not results:
        return False

    # 收集所有不同的 doc_id
    unique_docs = set()
    for r in results:
        doc_id = r.get('doc_id')
        if doc_id:
            unique_docs.add(doc_id)

    # 超過 1 個文件即為交叉查詢
    is_cross = len(unique_docs) > 1

    if is_cross:
        logger.info(f"檢測到交叉查詢: {len(unique_docs)} 個不同文件")
    else:
        logger.info(f"單一文件查詢: {len(unique_docs)} 個文件")

    return is_cross
