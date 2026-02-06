"""
Search Module - Legacy Search (v3.1 Adapter)
將傳統的關鍵字搜尋重寫為適配 v3 Schema (vec_chunks)
"""

import sqlite3
import logging
from typing import List, Dict, Optional
from config import DB_PATH
from core.database import get_connection

logger = logging.getLogger(__name__)


def _search_filename(
    cursor: sqlite3.Cursor,
    query: str,
    file_types: Optional[List[str]],
    top_k: int
) -> List[Dict]:
    """
    階段 0: 搜尋 filename 欄位
    此功能依然有效，因為 documents 表有 filename 欄位
    """
    type_condition = ""
    params = [f'%{query}%']
    
    if file_types:
        placeholders = ','.join(['?'] * len(file_types))
        type_condition = f"AND doc_type IN ({placeholders})"
        params.extend(file_types)
    
    params.append(top_k)
    
    # 注意: v3 schema 使用 'filename' 而非 'file_name'，使用 'doc_type' 而非 'file_type'
    sql = f"""
        SELECT 
            id,
            filename as file_name,
            doc_type as file_type,
            upload_date as upload_time,
            'File Match' as raw_content,
            'System' as author
        FROM documents
        WHERE filename LIKE ?
        {type_condition}
        ORDER BY upload_date DESC
        LIMIT ?
    """
    
    cursor.execute(sql, params)
    results = []
    for row in cursor.fetchall():
        doc = dict(row)
        doc['preview'] = f"檔案: {doc['file_name']}"
        doc['match_level'] = 'filename'
        results.append(doc)
    
    return results


def _search_content_text(
    cursor: sqlite3.Cursor,
    query: str,
    file_types: Optional[List[str]],
    top_k: int
) -> List[Dict]:
    """
    階段 1: 搜尋 vec_chunks 的文字內容 (text_content)
    取代舊版對 doc_knowledge 等表的 keywords/raw_content 搜尋
    """
    type_condition = ""
    params = [f'%{query}%']
    
    if file_types:
        placeholders = ','.join(['?'] * len(file_types))
        # 需要 JOIN documents 表來過濾 doc_type
        type_condition = f"AND d.doc_type IN ({placeholders})"
        params.extend(file_types)
    
    params.append(top_k)
    
    sql = f"""
        SELECT 
            d.id,
            d.filename as file_name,
            d.doc_type as file_type,
            d.upload_date as upload_time,
            v.text_content as raw_content,
            'System' as author
        FROM vec_chunks v
        JOIN documents d ON v.doc_id = d.id
        WHERE v.text_content LIKE ?
        {type_condition}
        GROUP BY d.id  -- 避免同一文件重複出現
        ORDER BY d.upload_date DESC
        LIMIT ?
    """
    
    cursor.execute(sql, params)
    results = []
    for row in cursor.fetchall():
        doc = dict(row)
        if doc['raw_content']:
            # 簡單預覽
            text = doc['raw_content']
            idx = text.lower().find(query.lower())
            start = max(0, idx - 50)
            end = min(len(text), idx + 150)
            doc['preview'] = ('...' if start > 0 else '') + text[start:end] + ('...' if end < len(text) else '')
        
        doc['match_level'] = 'content'
        results.append(doc)
    
    return results


def search_documents_v2(
    query: str,
    file_types: Optional[List[str]] = None,
    fuzzy: bool = True,
    top_k: int = 10
) -> List[Dict]:
    """
    v3.1 適配版搜尋
    
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
        
        # 1. 搜尋檔名
        results = _search_filename(cursor, query, file_types, top_k)
        if results:
            logger.info(f"✅ Filename 搜尋命中: {len(results)} 筆")
            conn.close()
            return results
        
        # 2. 搜尋內容
        results = _search_content_text(cursor, query, file_types, top_k)
        if results:
            logger.info(f"✅ Content 搜尋命中: {len(results)} 筆")
            conn.close()
            return results
            
        conn.close()
        logger.warning(f"❌ 無搜尋結果: '{query}'")
        return []
        
    except Exception as e:
        logger.error(f"搜尋失敗: {e}")
        return []


def search_by_field(
    file_type: str,
    field_name: str,
    query: str,
    top_k: int = 10
) -> List[Dict]:
    """
    保留介面，但在 v3 架構中，所有內容都在 vec_chunks.text_content
    此函式轉為對 content 的搜尋
    """
    return search_documents_v2(query, [file_type] if file_type else None, top_k=top_k)
