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

# 關鍵字匹配工具
from .keyword_matcher import (
    fuzzy_search_keywords,
    extract_potential_terms,
    get_all_keywords
)

__all__ = [
    # v2.0 傳統搜尋
    'search_documents_v2',
    'search_by_field',
    
    # v3.0 向量搜尋
    'search_by_vector',
    
    # v3.0 混合搜尋
    'hybrid_search',
    
    # 工具函數
    'fuzzy_search_keywords',
    'extract_potential_terms',
    'get_all_keywords',
]
