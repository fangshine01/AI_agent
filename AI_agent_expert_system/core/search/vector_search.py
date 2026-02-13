"""
Search Module - Vector Search (v3.0 + v2.3.0 快取優化)
向量相似度搜尋功能

v2.3.0 增強：
- Embedding 快取：避免重複查詢時重複呼叫 API
- 搜尋結果快取：5 分鐘 TTL 快取重複查詢
"""

import logging
from typing import List, Dict, Optional
from core import database, ai_core
from core.search.search_cache import (
    get_cached_embedding,
    cache_embedding,
    get_cached_search_results,
    cache_search_results,
)

logger = logging.getLogger(__name__)


def search_by_vector(
    query: str,
    top_k: int = 5,
    source_type: Optional[str] = None,
    filters: Optional[Dict] = None,
    api_key: str = None,
    base_url: str = None
) -> List[Dict]:
    """
    使用向量相似度搜尋（含快取優化）
    
    Args:
        query: 查詢文字
        top_k: 回傳前 k 筆結果
        source_type: 可選,過濾特定類型的切片
        filters: 結構化過濾條件
        api_key: API Key (選填)
        base_url: API Base URL (選填)
    
    Returns:
        List[Dict]: 搜尋結果
    """
    try:
        logger.info(f"開始向量搜尋: '{query}' (Filters: {filters})")
        
        # Phase 5: 檢查搜尋結果快取（無 filters 時才啟用，避免快取過多變體）
        if not filters:
            cached = get_cached_search_results(query, top_k=top_k, source_type=source_type)
            if cached is not None:
                logger.info(f"✅ 向量搜尋 (快取命中), 回傳 {len(cached)} 筆結果")
                return cached
        
        # 1. 取得查詢的 embedding（優先從快取取得）
        query_embedding = get_cached_embedding(query)
        if query_embedding is not None:
            usage = {"total_tokens": 0}  # 快取命中則不消耗 Token
            logger.debug(f"Embedding 快取命中: '{query[:30]}...'")
        else:
            query_embedding, usage = ai_core.get_embedding(
                query, 
                api_key=api_key,
                base_url=base_url
            )
            # 寫入 embedding 快取
            cache_embedding(query, query_embedding)
        
        # 記錄 Token（快取命中時 usage 為 0）
        if usage.get("total_tokens", 0) > 0:
            database.log_token_usage(
                file_name="System",
                operation='search_embedding',
                usage=usage
            )
        
        # 2. 使用向量搜尋
        chunks = database.search_by_vector(
            query_embedding=query_embedding,
            top_k=top_k,
            source_type=source_type,
            filters=filters
        )
        
        if not chunks:
            logger.info("向量搜尋無結果")
            return []
        
        # 3. 補充文件資訊
        results = []
        for chunk in chunks:
            doc = database.get_document(chunk['doc_id'])
            
            if doc:
                result = {
                    **chunk,
                    'document': {
                        'filename': doc['filename'],
                        'doc_type': doc['doc_type'],
                        'upload_date': doc['upload_date'],
                        'model_used': doc['model_used']
                    }
                }
                results.append(result)
        
        logger.info(f"✅ 向量搜尋完成, 找到 {len(results)} 筆結果")
        
        # Phase 5: 寫入搜尋結果快取（無 filters 時）
        if not filters and results:
            cache_search_results(query, results, top_k=top_k, source_type=source_type)
        
        return results
        
    except Exception as e:
        logger.error(f"❌ 向量搜尋失敗: {e}")
        return []
