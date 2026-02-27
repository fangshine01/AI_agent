# -*- coding: utf-8 -*-
"""
文件分組模組 (Document Grouping)

功能:
1. 將搜尋結果按 doc_id 分組
2. 動態選擇chunks (基於相似度閾值)
3. 控制token使用量 (訓練/問答雙模式)
4. 直接從資料庫提取摘要
"""

import logging
from typing import List, Dict, Optional
from core.database import get_connection

logger = logging.getLogger(__name__)


def group_chunks_by_document(
    chunks: List[Dict],
    mode: str = 'qa',
    similarity_thresholds: Dict[str, float] = None,
    token_budget: int = None
) -> Dict[int, Dict]:
    """
    將搜尋結果按 doc_id 分組,並動態選擇chunks
    
    Args:
        chunks: 搜尋結果列表
        mode: 'training' (無限制) 或 'qa' (問答模式)
        similarity_thresholds: 相似度閾值配置
        token_budget: token預算 (僅問答模式)
    
    Returns:
        Dict[doc_id, grouped_data]: 分組後的結果
    """
    if similarity_thresholds is None:
        similarity_thresholds = {
            'high': 0.85,
            'medium': 0.70,
            'low': 0.50
        }
    
    logger.info(f"開始文件分組 (模式: {mode}, 預算: {token_budget})")
    
    # 步驟 1: 按 doc_id 分組
    grouped = {}
    for chunk in chunks:
        doc_id = chunk.get('doc_id')
        if not doc_id:
            logger.warning(f"Chunk 缺少 doc_id: {chunk.get('chunk_id')}")
            continue
        
        if doc_id not in grouped:
            grouped[doc_id] = {
                'doc_id': doc_id,
                'document_info': chunk.get('document', {}),
                'all_chunks': [],
                'selected_chunks': [],
                'total_similarity': 0,
                'summary': None
            }
        
        grouped[doc_id]['all_chunks'].append(chunk)
    
    logger.info(f"分組完成: {len(chunks)} 個chunks -> {len(grouped)} 個文件")
    
    # 步驟 2: 為每個文件動態選擇chunks
    for doc_id, data in grouped.items():
        # 按相似度排序
        data['all_chunks'].sort(
            key=lambda x: x.get('similarity', x.get('total_score', 0)),
            reverse=True
        )
        
        # 動態選擇
        selected = select_chunks_dynamically(
            data['all_chunks'],
            mode=mode,
            thresholds=similarity_thresholds
        )
        
        data['selected_chunks'] = selected
        data['total_similarity'] = sum(
            c.get('similarity', c.get('total_score', 0)) for c in selected
        )
        
        logger.debug(
            f"文件 {doc_id}: {len(data['all_chunks'])} chunks -> "
            f"{len(selected)} 個被選中"
        )
    
    # 步驟 3: 提取文件摘要 (直接從資料庫)
    for doc_id, data in grouped.items():
        summary_data = extract_summary_from_db(doc_id)
        if summary_data:
            data['summary'] = summary_data
    
    # 步驟 4: 應用token預算 (僅問答模式)
    if mode == 'qa' and token_budget:
        grouped = apply_token_budget(grouped, token_budget)
    
    return grouped


def select_chunks_dynamically(
    chunks: List[Dict],
    mode: str = 'qa',
    thresholds: Dict[str, float] = None
) -> List[Dict]:
    """
    動態選擇chunks (基於相似度閾值)
    
    Args:
        chunks: 文件的所有chunks (已按相似度排序)
        mode: 'training' (無限制) 或 'qa' (問答模式)
        thresholds: 相似度閾值
    
    Returns:
        選擇的chunks列表
    """
    if thresholds is None:
        thresholds = {'high': 0.85, 'medium': 0.70, 'low': 0.50}
    
    if mode == 'training':
        # 訓練模式: 返回所有相關chunks
        logger.debug(f"訓練模式: 返回所有 {len(chunks)} 個chunks")
        return chunks
    
    # 問答模式: 動態選擇
    selected = []
    for chunk in chunks:
        # 支援多種分數類型: similarity (向量搜尋), match_score (關鍵字搜尋), total_score
        similarity = chunk.get('similarity', chunk.get('match_score', chunk.get('total_score', 0)))
        
        # 特殊處理: 如果是關鍵字搜尋 (有 match_level 欄位),直接選中
        if chunk.get('match_level') in ['filename', 'keywords', 'content']:
            selected.append(chunk)
            logger.debug(f"關鍵字匹配 ({chunk.get('match_level')}): 直接選中")
            continue
        
        if similarity > thresholds['high']:
            # 高相關度: 必選
            selected.append(chunk)
            logger.debug(f"高相關度 ({similarity:.3f}): 選中")
        elif similarity > thresholds['medium'] and len(selected) < 3:
            # 中等相關度: 最多3個
            selected.append(chunk)
            logger.debug(f"中等相關度 ({similarity:.3f}): 選中 ({len(selected)}/3)")
        elif len(selected) == 0 and similarity > thresholds['low']:
            # 至少保留1個 (若相似度不太低)
            selected.append(chunk)
            logger.debug(f"保底選擇 ({similarity:.3f}): 選中")
        else:
            logger.debug(f"相似度不足 ({similarity:.3f}): 跳過")
            break
    
    logger.info(f"動態選擇: {len(chunks)} -> {len(selected)} 個chunks")
    return selected


def extract_summary_from_db(doc_id: int) -> Optional[Dict]:
    """
    直接從資料庫提取文件摘要 (避免GPT二次處理)
    
    Args:
        doc_id: 文件ID
    
    Returns:
        Dict: {'summary': str, 'key_points': str, ...} 或 None
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT summary, key_points, filename, doc_type,
                   product_model, defect_code, station, yield_loss
            FROM documents 
            WHERE id = ?
            """,
            (doc_id,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if result:
            summary, key_points, filename, doc_type, product, defect, station, yield_loss = result
            
            # 即使 summary 為空，若有 8D欄位 也回傳
            if summary or product or defect:
                logger.debug(f"文件 {doc_id} ({filename}): 找到摘要/元數據")
                return {
                    'summary': summary,
                    'key_points': key_points,
                    'filename': filename,
                    'doc_type': doc_type,
                    'product_model': product,
                    'defect_code': defect,
                    'station': station,
                    'yield_loss': yield_loss
                }
            else:
                logger.debug(f"文件 {doc_id} ({filename}): 無摘要或元數據")
        
        return None
        
    except Exception as e:
        logger.error(f"提取摘要失敗 (doc_id={doc_id}): {e}")
        return None


def apply_token_budget(
    grouped: Dict[int, Dict],
    budget: int
) -> Dict[int, Dict]:
    """
    應用token預算 (問答模式)
    
    策略:
    1. 計算每個文件的token使用量
    2. 若超過預算,優先保留高相似度文件
    3. 截斷低相似度文件的chunks
    
    Args:
        grouped: 分組後的文件
        budget: token預算
    
    Returns:
        應用預算後的分組結果
    """
    logger.info(f"應用token預算: {budget} tokens")
    
    # 計算每個文件的token使用量
    for doc_id, data in grouped.items():
        total_tokens = 0
        for chunk in data['selected_chunks']:
            # 簡單估算: 中文約 1.5 tokens/字, 英文約 0.25 tokens/word
            content = chunk.get('content', chunk.get('raw_content', ''))
            estimated_tokens = len(content) * 1.5  # 保守估計
            total_tokens += estimated_tokens
        
        data['estimated_tokens'] = int(total_tokens)
    
    # 按總相似度排序文件
    sorted_docs = sorted(
        grouped.items(),
        key=lambda x: x[1]['total_similarity'],
        reverse=True
    )
    
    # 逐個加入文件,直到達到預算
    current_tokens = 0
    final_grouped = {}
    
    for doc_id, data in sorted_docs:
        doc_tokens = data['estimated_tokens']
        
        if current_tokens + doc_tokens <= budget:
            # 完整加入
            final_grouped[doc_id] = data
            current_tokens += doc_tokens
            logger.debug(
                f"文件 {doc_id}: 完整加入 ({doc_tokens} tokens, "
                f"累計: {current_tokens}/{budget})"
            )
        else:
            # 嘗試部分加入 (減少chunks)
            remaining_budget = budget - current_tokens
            if remaining_budget > 200:  # 至少保留200 tokens
                # 逐個加入chunks直到預算用完
                partial_chunks = []
                partial_tokens = 0
                
                for chunk in data['selected_chunks']:
                    content = chunk.get('content', chunk.get('raw_content', ''))
                    chunk_tokens = int(len(content) * 1.5)
                    
                    if partial_tokens + chunk_tokens <= remaining_budget:
                        partial_chunks.append(chunk)
                        partial_tokens += chunk_tokens
                    else:
                        break
                
                if partial_chunks:
                    data['selected_chunks'] = partial_chunks
                    data['estimated_tokens'] = partial_tokens
                    final_grouped[doc_id] = data
                    current_tokens += partial_tokens
                    logger.debug(
                        f"文件 {doc_id}: 部分加入 ({len(partial_chunks)} chunks, "
                        f"{partial_tokens} tokens)"
                    )
                else:
                    logger.debug(f"文件 {doc_id}: 預算不足,跳過")
            else:
                logger.debug(f"文件 {doc_id}: 預算已滿,跳過")
                break
    
    logger.info(
        f"Token預算應用完成: {len(final_grouped)}/{len(grouped)} 個文件, "
        f"使用 {current_tokens}/{budget} tokens"
    )
    
    return final_grouped


def format_grouped_results(
    grouped: Dict[int, Dict],
    include_summary: bool = True
) -> List[Dict]:
    """
    格式化分組結果供LLM使用
    
    Args:
        grouped: 分組後的文件
        include_summary: 是否包含摘要
    
    Returns:
        格式化後的結果列表
    """
    formatted = []
    
    for doc_id, data in grouped.items():
        doc_info = data['document_info']
        filename = doc_info.get('filename', 'Unknown')
        doc_type = doc_info.get('doc_type', 'Unknown')
        
        # 建立文件級別的結果
        doc_result = {
            'doc_id': doc_id,
            'file_name': filename,
            'file_type': doc_type,
            'chunk_count': len(data['selected_chunks']),
            'total_chunks': len(data['all_chunks']),
            'avg_similarity': (
                data['total_similarity'] / len(data['selected_chunks'])
                if data['selected_chunks'] else 0
            ),
            'chunks': []
        }
        
        # 加入摘要 (若有)
        if include_summary and data.get('summary'):
            summary_data = data['summary']
            doc_result['summary'] = summary_data.get('summary')
            doc_result['key_points'] = summary_data.get('key_points')
            
            # 加入 8D 元數據
            doc_result['product_model'] = summary_data.get('product_model')
            doc_result['defect_code'] = summary_data.get('defect_code')
            doc_result['station'] = summary_data.get('station')
            doc_result['yield_loss'] = summary_data.get('yield_loss')
        
        # 加入選中的chunks並組合 raw_content
        raw_content_parts = []
        for chunk in data['selected_chunks']:
            chunk_content = chunk.get('content', chunk.get('raw_content', ''))
            doc_result['chunks'].append({
                'chunk_id': chunk.get('chunk_id'),
                'title': chunk.get('source_title', chunk.get('title')),
                'content': chunk_content,
                'similarity': chunk.get('similarity', chunk.get('total_score', 0))
            })
            # 收集內容用於組合 raw_content
            if chunk_content:
                raw_content_parts.append(chunk_content)
        
        # 組合所有 chunks 的內容到 raw_content (用於直讀模式)
        if raw_content_parts:
            doc_result['raw_content'] = '\n\n'.join(raw_content_parts)
        else:
            doc_result['raw_content'] = ''
        
        formatted.append(doc_result)
    
    # 按平均相似度排序
    formatted.sort(key=lambda x: x['avg_similarity'], reverse=True)
    
    logger.info(f"格式化完成: {len(formatted)} 個文件")
    return formatted


if __name__ == "__main__":
    # 測試用
    logging.basicConfig(level=logging.DEBUG)
    print("文件分組模組載入成功")
