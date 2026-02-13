"""
Search Module - Unified Interface
統一的搜尋模組介面
"""

# v2.0 傳統搜尋
from .legacy_search import (
    search_documents_v2,
    search_by_field
)

# v3.0 向量搜尋
from .vector_search import search_by_vector

# v3.0 混合搜尋
from .hybrid_search import hybrid_search

# v4.0 通用查詢引擎 (新增)
from .query_router import (
    universal_search,
    QueryIntent,
    SearchStrategy,
    analyze_query_intent,
    select_search_strategy
)

# 語意重排序與查詢擴展 (新增)
from .reranker import (
    semantic_rerank,
    expand_query,
    reciprocal_rank_fusion
)

# 分詞工具 (新增)
from .tokenizer import (
    tokenize_query,
    extract_document_identifiers,
    contains_document_identifier
)

# 關鍵字匹配工具
from .keyword_matcher import (
    fuzzy_search_keywords,
    extract_potential_terms,
    get_all_keywords
)

# v2.3.0 搜尋快取與效能優化
from .search_cache import (
    get_all_cache_stats,
    invalidate_search_cache,
)

__all__ = [
    # v4.0 通用查詢引擎 (推薦使用)
    'universal_search',
    'QueryIntent',
    'SearchStrategy',
    
    # v3.0 混合搜尋
    'hybrid_search',
    
    # v3.0 向量搜尋
    'search_by_vector',
    
    # v2.0 傳統搜尋
    'search_documents_v2',
    'search_by_field',
    
    # 語意重排序
    'semantic_rerank',
    'expand_query',
    'reciprocal_rank_fusion',
    
    # 分詞工具
    'tokenize_query',
    'extract_document_identifiers',
    'contains_document_identifier',
    
    # 查詢分析
    'analyze_query_intent',
    'select_search_strategy',
    
    # 工具函數
    'fuzzy_search_keywords',
    'extract_potential_terms',
    'get_all_keywords',
    
    # v2.3.0 快取工具
    'get_all_cache_stats',
    'invalidate_search_cache',
]
