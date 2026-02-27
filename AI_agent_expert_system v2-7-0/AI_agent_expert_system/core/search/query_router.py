# -*- coding: utf-8 -*-
"""
查詢路由器模組

智慧分析查詢意圖並選擇最佳搜尋策略
"""

import logging
import time
from typing import List, Dict, Optional
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
    通用查詢引擎入口
    
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
    
    # 2. 選擇搜尋策略
    if auto_strategy:
        strategy = select_search_strategy(query, intent, doc_type)
    else:
        strategy = kwargs.get('strategy', SearchStrategy.HYBRID)
    
    # 強制修正策略 based on query_type
    if query_type == 'procedure':
        # Procedure 傾向於找文件或關鍵字
        strategy = SearchStrategy.HYBRID 
    elif query_type == 'troubleshooting':
        # Troubleshooting 需要語意與過濾
        strategy = SearchStrategy.HYBRID
        
    logger.info(f"搜尋策略: {strategy.value}")
    
    # 3. 執行搜尋
    results = _execute_search(query, strategy, top_k, doc_type, filters=filters, **kwargs)
    
    # 4. 後處理與排序優化 (含文件分組)
    mode = kwargs.get('mode', 'qa')  # 預設為問答模式
    results = _post_process_results(results, query, intent, mode=mode, query_type=query_type)
    
    
    # 5. Direct Retrieval Logic (Skip LLM)
    skip_llm = False
    
    # 用戶需求: 針對 SOP (Procedure)、Training 與 Knowledge (規格/參考資料)，找到檔案後直接匯出，不要讓 AI 思考/摘要
    if query_type in ['procedure', 'training', 'knowledge'] and results:
        # 強制啟用直讀模式 (只要有找到結果)
        skip_llm = True
        logger.info(f"強制啟用直讀模式 (Type: {query_type})")
            
    elif query_type == 'general' and results:
        # 一般查詢自動判斷: 若意圖是找步驟/文件 且結果是 Procedure/Training/Knowledge
        top_doc = results[0]
        score = top_doc.get('total_score', top_doc.get('similarity', 0))
        doc_type = top_doc.get('file_type', top_doc.get('doc_type'))
        
        # 條件 1: 意圖符合且分數不錯
        intent_match = intent in [QueryIntent.PROCEDURAL, QueryIntent.DOCUMENT_LOOKUP, QueryIntent.FACTUAL]
        
        # 條件 2: 文件類型是 SOP, Training 或 Knowledge
        type_match = doc_type in ['Procedure', 'Training', 'Knowledge']
        
        # 條件 3: 分數足夠高 (避免誤判)
        score_high = score > 0.75
        
        if (intent_match or type_match) and score_high:
            skip_llm = True
            logger.info(f"自動啟用直讀模式 (General -> {doc_type}, Score: {score:.2f})")
                 
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
            'cross_query': _is_cross_query(results)  # 新增:檢測是否為交叉查詢
        }
    }


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
        # Legacy search 暫未支援 filters, 但可透過 file_types 過濾
        fts = [filters['doc_type']] if filters and filters.get('doc_type') else ([doc_type] if doc_type else None)
        return search_documents_v2(query, file_types=fts, top_k=top_k)
    
    elif strategy == SearchStrategy.HYBRID:
        # Hybrid search 需傳遞 filters 給 vector search
        # 目前 hybrid_search 可能還沒支援 filters 參數, 需檢查
        # 若 hybrid_search 內部呼叫 search_by_vector, 需要修改 hybrid_search.py
        # 暫時直接傳給 search_by_vector (若 hybrid_search 未更新)
        # 這裡假設 hybrid_search 會接收 **kwargs 並傳給 vector_search
        return hybrid_search(query, top_k=top_k, filters=filters, **kwargs)
    
    elif strategy == SearchStrategy.DOCUMENT_NAME:
        # 檔名優先搜尋
        fts = [filters['doc_type']] if filters and filters.get('doc_type') else ([doc_type] if doc_type else None)
        keyword_results = search_documents_v2(query, file_types=fts, top_k=top_k, fuzzy=True)
        if keyword_results:
            return keyword_results
        # 降級到混合搜尋
        return hybrid_search(query, top_k=top_k, filters=filters, **kwargs)
    
    elif strategy == SearchStrategy.SEMANTIC_DEEP:
        # 深度語意搜尋
        results = search_by_vector(query, top_k=top_k * 3, filters=filters, **kwargs)
        # 使用 AI 重新排序
        from .reranker import semantic_rerank
        return semantic_rerank(results, query)[:top_k]
    
    return []


def _post_process_results(
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
            import config
            
            grouping_config = config.DOCUMENT_GROUPING
            
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



def _calculate_confidence(results: List[Dict]) -> float:
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


def _is_cross_query(results: List[Dict]) -> bool:
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
        
        # 提取結果 chunk IDs
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


if __name__ == "__main__":
    # 測試查詢路由器
    logging.basicConfig(level=logging.INFO)
    
    test_queries = [
        "N706 蝴蝶Mura 問題",
        "如何解決 ITO issue",
        "為什麼會出現 Oven Pin 異常",
        "找到 SOP-001 文件",
        "比較 A 和 B 的差異"
    ]
    
    print("查詢意圖分析測試:\n")
    for query in test_queries:
        intent = analyze_query_intent(query)
        strategy = select_search_strategy(query, intent)
        print(f"查詢: '{query}'")
        print(f"  意圖: {intent.value}")
        print(f"  策略: {strategy.value}\n")
