"""
Search Module - Hybrid Search (v3.0)
混合搜尋 (向量 + 關鍵字)
"""

import logging
from typing import List, Dict
from core import database
from .vector_search import search_by_vector
from .legacy_search import search_documents_v2

logger = logging.getLogger(__name__)


def hybrid_search(
    query: str,
    top_k: int = 10,
    vector_weight: float = 0.6,
    keyword_weight: float = 0.4,
    api_key: str = None,
    base_url: str = None
) -> List[Dict]:
    """
    混合搜尋 (向量 + 關鍵字)
    
    Args:
        query: 查詢文字
        top_k: 回傳前 k 筆結果
        vector_weight: 向量搜尋權重 (0-1)
        keyword_weight: 關鍵字搜尋權重 (0-1)
        api_key: API Key (選填)
        base_url: API Base URL (選填)
    
    Returns:
        List[Dict]: 融合後的搜尋結果
    """
    try:
        logger.info(f"開始混合搜尋: '{query}'")
        
        # 1. 向量搜尋
        vector_results = search_by_vector(
            query, 
            top_k=top_k * 2, 
            api_key=api_key,
            base_url=base_url
        )
        
        # 2. 關鍵字搜尋
        keyword_results = search_documents_v2(query, top_k=top_k * 2, fuzzy=True)
        
        # 3. 結果融合與評分
        merged_results = {}
        
        # 處理向量搜尋結果
        for idx, result in enumerate(vector_results):
            chunk_id = result['chunk_id']
            vector_score = result['similarity'] * vector_weight * (1 - idx / (len(vector_results) * 2))
            
            merged_results[chunk_id] = {
                'chunk_id': chunk_id,
                'doc_id': result['doc_id'],
                'title': result['source_title'],
                'content': result['content'],
                'document': result.get('document', {}),
                'vector_score': vector_score,
                'keyword_score': 0,
                'total_score': vector_score
            }
        
        # 處理關鍵字搜尋結果
        for idx, result in enumerate(keyword_results):
            doc_id = result['id']
            kw_score = keyword_weight * (1 - idx / (len(keyword_results) * 2))
            
            # 找到對應的切片
            chunks = database.get_chunks_by_doc_id(doc_id)
            for chunk in chunks:
                chunk_id = chunk['chunk_id']
                if chunk_id in merged_results:
                    merged_results[chunk_id]['keyword_score'] = kw_score
                    merged_results[chunk_id]['total_score'] += kw_score
                else:
                    merged_results[chunk_id] = {
                        'chunk_id': chunk_id,
                        'doc_id': doc_id,
                        'title': chunk['source_title'],
                        'content': chunk['content'],
                        'document': {
                            'filename': result['file_name'],
                            'doc_type': result['file_type']
                        },
                        'vector_score': 0,
                        'keyword_score': kw_score,
                        'total_score': kw_score
                    }
        
        # 4. 排序並回傳 top_k
        final_results = sorted(
            merged_results.values(),
            key=lambda x: x['total_score'],
            reverse=True
        )[:top_k]
        
        logger.info(f"✅ 混合搜尋完成, 融合 {len(vector_results)} 向量 + {len(keyword_results)} 關鍵字")
        logger.info(f"   最終回傳: {len(final_results)} 筆")
        
        return final_results
        
    except Exception as e:
        logger.error(f"❌ 混合搜尋失敗: {e}")
        # 降級:只使用向量搜尋
        # 降級:只使用向量搜尋
        return search_by_vector(
            query, 
            top_k=top_k, 
            api_key=api_key,
            base_url=base_url
        )
