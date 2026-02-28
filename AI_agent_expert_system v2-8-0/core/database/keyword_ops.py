"""
關鍵字操作模組
負責 document_keywords 表的 CRUD 操作
"""

import logging
from typing import Dict, List, Optional, Tuple
from .connection import get_connection

logger = logging.getLogger(__name__)


def save_document_keywords(doc_id: int, keywords: Dict[str, List[str]], source: str = 'ai', confidence: float = 1.0):
    """
    儲存文件關鍵字到 document_keywords 表
    
    Args:
        doc_id: 文件 ID
        keywords: 關鍵字字典, e.g. {'產品': ['N706'], 'Defect Code': ['蝴蝶Mura']}
        source: 來源 ('manual' or 'ai')
        confidence: AI 提取的信心度 (0-1)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        inserted = 0
        for category, keyword_list in keywords.items():
            for keyword in keyword_list:
                if not keyword or not keyword.strip():
                    continue
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO document_keywords 
                            (doc_id, category, keyword, confidence, source)
                        VALUES (?, ?, ?, ?, ?)
                    """, (doc_id, category, keyword.strip(), confidence, source))
                    if cursor.rowcount > 0:
                        inserted += 1
                except Exception as e:
                    logger.warning(f"插入關鍵字失敗 ({category}:{keyword}): {e}")
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ 已儲存 {inserted} 個關鍵字 (doc_id: {doc_id})")
        return inserted
        
    except Exception as e:
        logger.error(f"❌ 儲存文件關鍵字失敗: {e}")
        return 0


def get_document_keywords(doc_id: int) -> Dict[str, List[str]]:
    """
    取得文件的所有關鍵字 (按類別分組)
    
    Args:
        doc_id: 文件 ID
    
    Returns:
        Dict[str, List[str]]: e.g. {'產品': ['N706'], 'Defect Code': ['蝴蝶Mura']}
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT category, keyword, confidence
            FROM document_keywords
            WHERE doc_id = ?
            ORDER BY category, confidence DESC
        """, (doc_id,))
        
        results = {}
        for row in cursor.fetchall():
            category, keyword, confidence = row
            if category not in results:
                results[category] = []
            results[category].append(keyword)
        
        conn.close()
        return results
        
    except Exception as e:
        logger.error(f"❌ 取得文件關鍵字失敗: {e}")
        return {}


def search_by_keywords(filters: Dict[str, str]) -> List[int]:
    """
    根據關鍵字過濾查詢文件 ID
    
    Args:
        filters: 關鍵字篩選條件, e.g. {'產品': 'N706', 'Defect Code': '蝴蝶Mura'}
    
    Returns:
        List[int]: 符合條件的 doc_id 列表
    """
    if not filters:
        return []
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 建立動態 SQL - 使用多個 JOIN 實現 AND 邏輯
        query = "SELECT DISTINCT dk0.doc_id FROM document_keywords dk0"
        conditions = ["dk0.category = ? AND dk0.keyword LIKE ?"]
        params = [list(filters.keys())[0], f"%{list(filters.values())[0]}%"]
        
        for i, (category, keyword) in enumerate(filters.items()):
            if i == 0:
                continue
            alias = f"dk{i}"
            query += f" JOIN document_keywords {alias} ON dk0.doc_id = {alias}.doc_id"
            conditions.append(f"{alias}.category = ? AND {alias}.keyword LIKE ?")
            params.extend([category, f"%{keyword}%"])
        
        query += " WHERE " + " AND ".join(conditions)
        
        cursor.execute(query, params)
        doc_ids = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        logger.debug(f"✅ 關鍵字搜尋完成, 找到 {len(doc_ids)} 筆 (filters: {filters})")
        return doc_ids
        
    except Exception as e:
        logger.error(f"❌ 關鍵字搜尋失敗: {e}")
        return []


def delete_document_keywords(doc_id: int) -> int:
    """
    刪除文件的所有關鍵字
    
    Args:
        doc_id: 文件 ID
    
    Returns:
        int: 刪除的記錄數
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM document_keywords WHERE doc_id = ?", (doc_id,))
        deleted = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ 已刪除 {deleted} 個關鍵字 (doc_id: {doc_id})")
        return deleted
        
    except Exception as e:
        logger.error(f"❌ 刪除文件關鍵字失敗: {e}")
        return 0


def get_keywords_by_category(category: str) -> List[Dict]:
    """
    取得特定類別的所有關鍵字及其使用頻率
    
    Args:
        category: 關鍵字類別
    
    Returns:
        List[Dict]: [{'keyword': 'N706', 'count': 5, 'doc_ids': [1,2,3]}]
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT keyword, COUNT(DISTINCT doc_id) as doc_count,
                   GROUP_CONCAT(DISTINCT doc_id) as doc_ids
            FROM document_keywords
            WHERE category = ?
            GROUP BY keyword
            ORDER BY doc_count DESC
        """, (category,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'keyword': row[0],
                'count': row[1],
                'doc_ids': [int(x) for x in row[2].split(',')] if row[2] else []
            })
        
        conn.close()
        return results
        
    except Exception as e:
        logger.error(f"❌ 取得類別關鍵字失敗: {e}")
        return []
