"""
Search Module - Vector Search (v3.0)
向量相似度搜尋功能
"""

import logging
from typing import List, Dict, Optional
from core import database, ai_core

logger = logging.getLogger(__name__)


def search_by_vector(
    query: str,
    top_k: int = 5,
    source_type: Optional[str] = None,
    api_key: str = None,
    base_url: str = None
) -> List[Dict]:
    """
    使用向量相似度搜尋
    
    Args:
        query: 查詢文字
        top_k: 回傳前 k 筆結果
        source_type: 可選,過濾特定類型的切片
        api_key: API Key (選填)
        base_url: API Base URL (選填)
    
    Returns:
        List[Dict]: 搜尋結果
    """
    try:
        logger.info(f"開始向量搜尋: '{query}'")
        
        # 1. 取得查詢的 embedding
        query_embedding, usage = ai_core.get_embedding(
            query, 
            api_key=api_key,
            base_url=base_url
        )
        
        # 記錄 Token
        database.log_token_usage(
            file_name="System",
            operation='search_embedding',
            usage=usage
        )
        
        # 2. 使用向量搜尋
        chunks = database.search_by_vector(
            query_embedding=query_embedding,
            top_k=top_k,
            source_type=source_type
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
        return results
        
    except Exception as e:
        logger.error(f"❌ 向量搜尋失敗: {e}")
        return []
