# -*- coding: utf-8 -*-
"""
查詢路由器模組

智慧分析查詢意圖並選擇最佳搜尋策略
（v5.1 — 拆分後的 orchestrator，核心邏輯已遷移至子模組）

子模組:
  intent_analyzer.py  — QueryIntent / SearchStrategy 列舉 + 意圖/策略選擇
  troubleshooting_matcher.py — Troubleshooting 精準匹配
  post_processor.py   — 去重、標準化、文件分組、信心度、交叉查詢檢測
"""

import logging
import time
from typing import List, Dict, Optional

# --- 從子模組匯入公開 API ---
from .intent_analyzer import (                          # noqa: F401
    QueryIntent,
    SearchStrategy,
    analyze_query_intent,
    select_search_strategy,
)
from .troubleshooting_matcher import (
    try_exact_troubleshooting_match as _try_exact_troubleshooting_match,
)
from .post_processor import (
    post_process_results  as _post_process_results,
    calculate_confidence  as _calculate_confidence,
    is_cross_query        as _is_cross_query,
)

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────
# 通用查詢引擎入口
# ────────────────────────────────────────────

def universal_search(
    query: str,
    top_k: int = 10,
    doc_type: Optional[str] = None,
    auto_strategy: bool = True,
    query_type: str = 'general',
    filters: Optional[Dict] = None,
    **kwargs
) -> Dict:
    """
    通用查詢引擎入口 (v5.0 - 支援精準匹配與直讀模式)

    Args:
        query: 查詢文字
        top_k: 回傳結果數
        doc_type: 限定文件類型
        auto_strategy: 是否自動選擇策略
        query_type: 查詢類型 (general, troubleshooting, procedure, knowledge)
        filters: 結構化過濾條件

    Returns:
        Dict: 搜尋結果
    """
    start_time = time.time()

    # 1. 分析查詢意圖 (若有明確 query_type, 則以此為主)
    if query_type != 'general':
        # 簡單映射
        if query_type == 'procedure':
            intent = QueryIntent.PROCEDURAL
        elif query_type == 'troubleshooting':
            intent = QueryIntent.TROUBLESHOOTING
        elif query_type == 'knowledge':
            intent = QueryIntent.FACTUAL
        else:
            intent = analyze_query_intent(query)
    else:
        intent = analyze_query_intent(query)

    logger.info(f"查詢意圖: {intent.value} (Type: {query_type})")

    # 2. Troubleshooting 精準匹配
    if query_type == 'troubleshooting' or intent == QueryIntent.TROUBLESHOOTING:
        exact_result = _try_exact_troubleshooting_match(query, filters)
        if exact_result:
            search_time = time.time() - start_time
            _log_search_history(query, intent, SearchStrategy.HYBRID, [exact_result], search_time)

            return {
                'query': query,
                'intent': intent.value,
                'strategy': 'exact_match',
                'results': [exact_result],
                'meta': {
                    'total_found': 1,
                    'search_time': search_time,
                    'confidence': 1.0,
                    'skip_llm': True,
                    'cross_query': False,
                    'mode': 'direct'
                }
            }

    # 3. 選擇搜尋策略
    if auto_strategy:
        strategy = select_search_strategy(query, intent, doc_type)
    else:
        strategy = kwargs.get('strategy', SearchStrategy.HYBRID)

    # 強制修正策略 based on query_type
    if query_type == 'procedure':
        strategy = SearchStrategy.HYBRID
    elif query_type == 'troubleshooting':
        strategy = SearchStrategy.HYBRID

    logger.info(f"搜尋策略: {strategy.value}")

    # 4. 執行搜尋
    results = _execute_search(query, strategy, top_k, doc_type, filters=filters, **kwargs)

    # 5. 後處理與排序優化 (含文件分組)
    mode = kwargs.get('mode', 'qa')
    results = _post_process_results(results, query, intent, mode=mode, query_type=query_type)

    # 6. Direct Retrieval Logic (Skip LLM)
    skip_llm = _should_skip_llm(query_type, intent, results)

    # 記錄查詢歷史
    search_time = time.time() - start_time
    _log_search_history(query, intent, strategy, results, search_time)

    return {
        'query': query,
        'intent': intent.value,
        'strategy': strategy.value,
        'results': results[:top_k],
        'meta': {
            'total_found': len(results),
            'search_time': search_time,
            'confidence': _calculate_confidence(results),
            'skip_llm': skip_llm,
            'cross_query': _is_cross_query(results)
        }
    }


# ────────────────────────────────────────────
# 內部輔助函數
# ────────────────────────────────────────────

def _should_skip_llm(query_type: str, intent: QueryIntent, results: List[Dict]) -> bool:
    """
    判斷是否應跳過 LLM 總結 (v5.0)

    直讀模式適用於:
    - SOP / Procedure 查詢
    - Training 教材查詢
    - Knowledge 技術文件查詢
    - Troubleshooting 查詢 (已有完整 8D 報告)
    """
    if not results:
        return False

    # 明確類型查詢: 強制直讀
    if query_type in ['procedure', 'training', 'knowledge', 'troubleshooting']:
        logger.info(f"強制啟用直讀模式 (Type: {query_type})")
        return True

    # 一般查詢: 自動判斷
    if query_type == 'general':
        top_doc = results[0]
        score = top_doc.get('total_score', top_doc.get('similarity', 0))
        top_doc_type = top_doc.get('file_type', top_doc.get('doc_type'))

        intent_match = intent in [QueryIntent.PROCEDURAL, QueryIntent.DOCUMENT_LOOKUP, QueryIntent.FACTUAL]
        type_match = top_doc_type in ['Procedure', 'Training', 'Knowledge', 'Troubleshooting']
        score_high = score > 0.75

        if (intent_match or type_match) and score_high:
            logger.info(f"自動啟用直讀模式 (General -> {top_doc_type}, Score: {score:.2f})")
            return True

    return False


def _execute_search(
    query: str,
    strategy: SearchStrategy,
    top_k: int,
    doc_type: Optional[str],
    filters: Optional[Dict] = None,
    **kwargs
) -> List[Dict]:
    """執行實際搜尋"""
    from .vector_search import search_by_vector
    from .legacy_search import search_documents_v2
    from .hybrid_search import hybrid_search

    if strategy == SearchStrategy.VECTOR_ONLY:
        return search_by_vector(query, top_k=top_k, filters=filters, **kwargs)

    elif strategy == SearchStrategy.KEYWORD_ONLY:
        fts = [filters['doc_type']] if filters and filters.get('doc_type') else ([doc_type] if doc_type else None)
        return search_documents_v2(query, file_types=fts, top_k=top_k)

    elif strategy == SearchStrategy.HYBRID:
        return hybrid_search(query, top_k=top_k, filters=filters, **kwargs)

    elif strategy == SearchStrategy.DOCUMENT_NAME:
        fts = [filters['doc_type']] if filters and filters.get('doc_type') else ([doc_type] if doc_type else None)
        keyword_results = search_documents_v2(query, file_types=fts, top_k=top_k, fuzzy=True)
        if keyword_results:
            return keyword_results
        return hybrid_search(query, top_k=top_k, filters=filters, **kwargs)

    elif strategy == SearchStrategy.SEMANTIC_DEEP:
        results = search_by_vector(query, top_k=top_k * 3, filters=filters, **kwargs)
        from .reranker import semantic_rerank
        return semantic_rerank(results, query)[:top_k]

    return []


def _log_search_history(
    query: str,
    intent: QueryIntent,
    strategy: SearchStrategy,
    results: List[Dict],
    search_time: float
):
    """記錄查詢歷史 (用於後續優化)"""
    try:
        from core.database import log_search_history
        import json

        chunk_ids = [r.get('chunk_id') for r in results if r.get('chunk_id')]
        result_chunks = json.dumps(chunk_ids) if chunk_ids else None

        log_search_history(
            query=query,
            intent=intent.value,
            strategy=strategy.value,
            result_count=len(results),
            search_time=search_time,
            result_chunks=result_chunks
        )
    except Exception as e:
        logger.warning(f"記錄查詢歷史失敗: {e}")
