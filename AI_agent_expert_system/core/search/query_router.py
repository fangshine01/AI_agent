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
    
    # 2. ===== v5.0 新增: Troubleshooting 精準匹配 =====
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
                    'mode': 'direct'  # 標記為精準匹配直讀模式
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
    
    
    # 6. Direct Retrieval Logic (Skip LLM) - v5.0 強化版
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


def _try_exact_troubleshooting_match(query: str, filters: Optional[Dict] = None) -> Optional[Dict]:
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


def _should_skip_llm(query_type: str, intent: QueryIntent, results: List[Dict]) -> bool:
    """
    判斷是否應跳過 LLM 總結 (v5.0)
    
    直讀模式適用於:
    - SOP / Procedure 查詢
    - Training 教材查詢
    - Knowledge 技術文件查詢
    - Troubleshooting 查詢 (已有完整 8D 報告)
    
    Returns:
        bool: True 表示跳過 LLM, 直接回傳
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
        
        # 條件 1: 意圖符合
        intent_match = intent in [QueryIntent.PROCEDURAL, QueryIntent.DOCUMENT_LOOKUP, QueryIntent.FACTUAL]
        
        # 條件 2: 文件類型適合直讀
        type_match = top_doc_type in ['Procedure', 'Training', 'Knowledge', 'Troubleshooting']
        
        # 條件 3: 分數足夠高
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
