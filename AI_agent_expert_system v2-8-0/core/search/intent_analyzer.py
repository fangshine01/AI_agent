# -*- coding: utf-8 -*-
"""
查詢意圖分析模組

提供 QueryIntent/SearchStrategy 列舉及意圖分析、策略選擇函數
"""

import logging
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


class QueryIntent(Enum):
    """查詢意圖類型"""
    FACTUAL = "factual"              # 事實查詢 (例: 什麼是...)
    PROCEDURAL = "procedural"        # 步驟查詢 (例: 如何...)
    TROUBLESHOOTING = "troubleshooting"  # 問題排查 (例: 為什麼...、怎麼修...)
    COMPARATIVE = "comparative"      # 比較查詢 (例: A和B的差異)
    DOCUMENT_LOOKUP = "document_lookup"  # 文件查找 (例: 找到XX文件)


class SearchStrategy(Enum):
    """搜尋策略"""
    VECTOR_ONLY = "vector"           # 純向量搜尋
    KEYWORD_ONLY = "keyword"         # 純關鍵字
    HYBRID = "hybrid"                # 混合搜尋
    DOCUMENT_NAME = "document_name"  # 檔名搜尋
    SEMANTIC_DEEP = "semantic_deep"  # 深度語意搜尋


def analyze_query_intent(query: str) -> QueryIntent:
    """
    分析查詢意圖

    使用規則判斷

    Args:
        query: 查詢字串

    Returns:
        QueryIntent: 查詢意圖
    """
    query_lower = query.lower()

    # 規則判斷
    if any(word in query_lower for word in ['如何', '怎麼', '步驟', '流程', 'how to', 'how do']):
        return QueryIntent.PROCEDURAL

    if any(word in query_lower for word in ['為什麼', '原因', '異常', '錯誤', '故障', 'why', 'error', 'issue', 'problem']):
        return QueryIntent.TROUBLESHOOTING

    if any(word in query_lower for word in ['差異', '比較', '區別', 'vs', 'compare', 'difference']):
        return QueryIntent.COMPARATIVE

    if any(word in query_lower for word in ['文件', '檔案', '找到', 'document', 'file', 'find']):
        return QueryIntent.DOCUMENT_LOOKUP

    # 預設為事實查詢
    return QueryIntent.FACTUAL


def select_search_strategy(
    query: str,
    intent: QueryIntent,
    doc_type: Optional[str] = None
) -> SearchStrategy:
    """
    根據查詢意圖選擇最佳搜尋策略

    Args:
        query: 查詢字串
        intent: 查詢意圖
        doc_type: 文件類型

    Returns:
        SearchStrategy: 搜尋策略
    """
    from .tokenizer import contains_document_identifier

    # 如果查詢包含明確文件名/編號,優先檔名搜尋
    if contains_document_identifier(query):
        return SearchStrategy.DOCUMENT_NAME

    # 根據意圖選擇
    strategy_map = {
        QueryIntent.DOCUMENT_LOOKUP: SearchStrategy.DOCUMENT_NAME,
        QueryIntent.FACTUAL: SearchStrategy.HYBRID,
        QueryIntent.PROCEDURAL: SearchStrategy.VECTOR_ONLY,
        QueryIntent.TROUBLESHOOTING: SearchStrategy.HYBRID,
        QueryIntent.COMPARATIVE: SearchStrategy.SEMANTIC_DEEP
    }

    return strategy_map.get(intent, SearchStrategy.HYBRID)
