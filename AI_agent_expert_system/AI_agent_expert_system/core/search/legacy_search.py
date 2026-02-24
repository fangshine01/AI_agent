"""
Search Module - Legacy Search (v3.1 Adapter)
將傳統的關鍵字搜尋重寫為適配 v3 Schema (vec_chunks)
支援多關鍵字 OR 搜尋以提升召回率
"""

import sqlite3
import logging
from typing import List, Dict, Optional
from config import DB_PATH
from core.database import get_connection
from .tokenizer import tokenize_query

logger = logging.getLogger(__name__)


def _search_filename(
    cursor: sqlite3.Cursor,
    keywords: List[str],
    file_types: Optional[List[str]],
    top_k: int
) -> List[Dict]:
    """
    階段 0: 搜尋 filename 欄位 (支援多關鍵字 OR 搜尋)
    此功能依然有效,因為 documents 表有 filename 欄位
    
    Args:
        cursor: 資料庫游標
        keywords: 關鍵字列表 (已分詞)
        file_types: 限定文件類型
        top_k: 返回結果數量
    """
    if not keywords:
        return []
    
    # 建立多個 LIKE 條件 (OR 連接)
    like_conditions = ' OR '.join(['d.filename LIKE ? COLLATE NOCASE' for _ in keywords])
    params = [f'%{kw}%' for kw in keywords]
    
    type_condition = ""
    if file_types:
        placeholders = ','.join(['?'] * len(file_types))
        type_condition = f"AND d.doc_type IN ({placeholders})"
        params.extend(file_types)
    
    # 計算匹配分數 (匹配的關鍵字越多,分數越高)
    match_score_expr = ' + '.join([f"(d.filename LIKE ? COLLATE NOCASE)" for _ in keywords])
    score_params = [f'%{kw}%' for kw in keywords]
    
    params.append(top_k)
    
    # 修改: JOIN vec_chunks 以取得實際內容
    sql = f"""
        SELECT 
            d.id,
            d.filename as file_name,
            d.doc_type as file_type,
            d.upload_date as upload_time,
            v.text_content as raw_content,
            v.chunk_id,
            v.source_type,
            'System' as author,
            ({match_score_expr}) as match_score
        FROM documents d
        LEFT JOIN vec_chunks v ON d.id = v.doc_id
        WHERE ({like_conditions})
        {type_condition}
        ORDER BY match_score DESC, d.upload_date DESC
        LIMIT ?
    """
    
    # 合併參數: LIKE 條件 + match_score 計算 + 類型過濾 + LIMIT
    all_params = params[:len(keywords)] + score_params
    if file_types:
        all_params.extend(file_types)
    all_params.append(top_k)
    
    cursor.execute(sql, all_params)
    results = []
    for row in cursor.fetchall():
        doc = dict(row)
        # 如果有內容,建立預覽
        if doc.get('raw_content'):
            preview_text = doc['raw_content'][:200]
            doc['preview'] = preview_text + ('...' if len(doc['raw_content']) > 200 else '')
        else:
            doc['preview'] = f"檔案: {doc['file_name']} (匹配度: {doc.get('match_score', 0)})"
        doc['match_level'] = 'filename'
        results.append(doc)
    
    return results


def _search_content_text(
    cursor: sqlite3.Cursor,
    keywords: List[str],
    file_types: Optional[List[str]],
    top_k: int
) -> List[Dict]:
    """
    階段 1: 搜尋 vec_chunks 的文字內容 (text_content)
    取代舊版對 doc_knowledge 等表的 keywords/raw_content 搜尋
    支援多關鍵字 OR 搜尋
    
    Args:
        cursor: 資料庫游標
        keywords: 關鍵字列表 (已分詞)
        file_types: 限定文件類型
        top_k: 返回結果數量
    """
    if not keywords:
        return []
    
    # 建立多個 LIKE 條件 (OR 連接)
    like_conditions = ' OR '.join(['v.text_content LIKE ? COLLATE NOCASE' for _ in keywords])
    params = [f'%{kw}%' for kw in keywords]
    
    type_condition = ""
    if file_types:
        placeholders = ','.join(['?'] * len(file_types))
        # 需要 JOIN documents 表來過濾 doc_type
        type_condition = f"AND d.doc_type IN ({placeholders})"
        params.extend(file_types)
    
    # 計算匹配分數
    match_score_expr = ' + '.join([f"(v.text_content LIKE ? COLLATE NOCASE)" for _ in keywords])
    score_params = [f'%{kw}%' for kw in keywords]
    
    params.append(top_k)
    
    sql = f"""
        SELECT 
            d.id,
            d.filename as file_name,
            d.doc_type as file_type,
            d.upload_date as upload_time,
            v.text_content as raw_content,
            'System' as author,
            ({match_score_expr}) as match_score
        FROM vec_chunks v
        JOIN documents d ON v.doc_id = d.id
        WHERE ({like_conditions})
        {type_condition}
        GROUP BY d.id  -- 避免同一文件重複出現
        ORDER BY match_score DESC, d.upload_date DESC
        LIMIT ?
    """
    
    # 合併參數
    all_params = params[:len(keywords)] + score_params
    if file_types:
        all_params.extend(file_types)
    all_params.append(top_k)
    
    cursor.execute(sql, all_params)
    results = []
    for row in cursor.fetchall():
        doc = dict(row)
        if doc['raw_content']:
            # 簡單預覽 - 顯示第一個匹配的關鍵字周圍的文字
            text = doc['raw_content']
            preview_created = False
            for kw in keywords:
                idx = text.lower().find(kw.lower())
                if idx >= 0:
                    start = max(0, idx - 50)
                    end = min(len(text), idx + 150)
                    doc['preview'] = ('...' if start > 0 else '') + text[start:end] + ('...' if end < len(text) else '')
                    preview_created = True
                    break
            
            if not preview_created:
                doc['preview'] = text[:200] + ('...' if len(text) > 200 else '')
        
        doc['match_level'] = 'content'
        results.append(doc)
    
    return results


def _search_keywords(
    cursor: sqlite3.Cursor,
    keywords: List[str],
    file_types: Optional[List[str]],
    top_k: int
) -> List[Dict]:
    """
    階段 2: 搜尋 vec_chunks 的 keywords 欄位
    利用已提取的結構化關鍵字進行精準搜尋
    
    Args:
        cursor: 資料庫游標
        keywords: 關鍵字列表 (已分詞)
        file_types: 限定文件類型
        top_k: 返回結果數量
    """
    if not keywords:
        return []
    
    # 建立多個 LIKE 條件 (OR 連接)
    like_conditions = ' OR '.join(['v.keywords LIKE ? COLLATE NOCASE' for _ in keywords])
    params = [f'%{kw}%' for kw in keywords]
    
    type_condition = ""
    if file_types:
        placeholders = ','.join(['?'] * len(file_types))
        type_condition = f"AND d.doc_type IN ({placeholders})"
        params.extend(file_types)
    
    params.append(top_k)
    
    sql = f"""
        SELECT 
            d.id,
            d.filename as file_name,
            d.doc_type as file_type,
            d.upload_date as upload_time,
            GROUP_CONCAT(DISTINCT v.keywords, '; ') as raw_content,
            'System' as author,
            COUNT(*) as match_count
        FROM vec_chunks v
        JOIN documents d ON v.doc_id = d.id
        WHERE ({like_conditions})
        {type_condition}
        GROUP BY d.id
        ORDER BY match_count DESC, d.upload_date DESC
        LIMIT ?
    """
    
    cursor.execute(sql, params)
    results = []
    for row in cursor.fetchall():
        doc = dict(row)
        doc['preview'] = f"關鍵字匹配: {doc.get('raw_content', '')[:200]}"
        doc['match_level'] = 'keywords'
        results.append(doc)
    
    return results


def search_documents_v2(
    query: str,
    file_types: Optional[List[str]] = None,
    fuzzy: bool = True,
    top_k: int = 10
) -> List[Dict]:
    """
    v3.1 適配版搜尋 (支援多關鍵字 OR 搜尋)
    
    Args:
        query: 搜尋關鍵字
        file_types: 限定文件類型
        fuzzy: 是否啟用模糊搜尋 (在此實現中簡化為 LIKE 搜尋)
        top_k: 返回結果數量
    
    Returns:
        List[Dict]: 搜尋結果
    """
    try:
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 分詞
        keywords = tokenize_query(query)
        logger.info(f"🔍 查詢分詞: '{query}' -> {keywords}")
        
        # 1. 搜尋檔名 (多關鍵字)
        results = _search_filename(cursor, keywords, file_types, top_k)
        if results:
            logger.info(f"✅ Filename 搜尋命中: {len(results)} 筆")
            conn.close()
            return results
        
        # 2. 搜尋 keywords 欄位
        results = _search_keywords(cursor, keywords, file_types, top_k)
        if results:
            logger.info(f"✅ Keywords 搜尋命中: {len(results)} 筆")
            conn.close()
            return results
        
        # 3. 搜尋內容 (多關鍵字)
        results = _search_content_text(cursor, keywords, file_types, top_k)
        if results:
            logger.info(f"✅ Content 搜尋命中: {len(results)} 筆")
            conn.close()
            return results
            
        conn.close()
        logger.warning(f"❌ 無搜尋結果: '{query}' (關鍵字: {keywords})")
        return []
        
    except Exception as e:
        logger.error(f"搜尋失敗: {e}", exc_info=True)
        return []


def search_by_field(
    file_type: str,
    field_name: str,
    query: str,
    top_k: int = 10
) -> List[Dict]:
    """
    保留介面,但在 v3 架構中,所有內容都在 vec_chunks.text_content
    此函式轉為對 content 的搜尋
    """
    return search_documents_v2(query, [file_type] if file_type else None, top_k=top_k)
