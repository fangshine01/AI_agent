"""
原始資料操作模組
負責 document_raw_data 表的 CRUD 操作
"""

import os
import logging
from typing import Optional, Dict, List
from .connection import get_connection

logger = logging.getLogger(__name__)


def save_raw_data(doc_id: int, raw_content: str, content_type: str = 'text',
                  file_extension: str = None) -> bool:
    """
    儲存文件的原始文字內容
    
    Args:
        doc_id: 文件 ID
        raw_content: 原始文字內容
        content_type: 內容類型 ('text', 'markdown', 'html')
        file_extension: 原始檔案副檔名
    
    Returns:
        bool: 是否成功
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO document_raw_data 
                (doc_id, raw_content, content_type, file_extension)
            VALUES (?, ?, ?, ?)
        """, (doc_id, raw_content, content_type, file_extension))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Raw data 已儲存 (doc_id: {doc_id}, length: {len(raw_content)})")
        return True
        
    except Exception as e:
        logger.error(f"❌ 儲存 Raw data 失敗: {e}")
        return False


def get_raw_data(doc_id: int) -> Optional[str]:
    """
    取得文件的原始文字內容
    
    Args:
        doc_id: 文件 ID
    
    Returns:
        Optional[str]: 原始文字內容
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT raw_content FROM document_raw_data WHERE doc_id = ?",
            (doc_id,)
        )
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            return result[0]
        return None
        
    except Exception as e:
        logger.error(f"❌ 取得 Raw data 失敗: {e}")
        return None


def get_raw_data_info(doc_id: int) -> Optional[Dict]:
    """
    取得原始資料的完整資訊 (含元資訊)
    
    Args:
        doc_id: 文件 ID
    
    Returns:
        Optional[Dict]: 原始資料資訊
    """
    try:
        conn = get_connection()
        conn.row_factory = lambda cursor, row: {
            col[0]: row[idx] for idx, col in enumerate(cursor.description)
        }
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM document_raw_data WHERE doc_id = ?",
            (doc_id,)
        )
        result = cursor.fetchone()
        
        conn.close()
        return result
        
    except Exception as e:
        logger.error(f"❌ 取得 Raw data info 失敗: {e}")
        return None


def delete_raw_data(doc_id: int) -> bool:
    """
    刪除文件的原始資料
    
    Args:
        doc_id: 文件 ID
    
    Returns:
        bool: 是否成功
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM document_raw_data WHERE doc_id = ?", (doc_id,))
        deleted = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        
        if deleted:
            logger.info(f"✅ Raw data 已刪除 (doc_id: {doc_id})")
        return deleted
        
    except Exception as e:
        logger.error(f"❌ 刪除 Raw data 失敗: {e}")
        return False


def get_all_raw_data(doc_type: str = None) -> List[Dict]:
    """
    取得所有文件的原始內容 (用於重新訓練)
    
    Args:
        doc_type: 過濾文件類型 (可選)
    
    Returns:
        List[Dict]: [{'doc_id': int, 'filename': str, 'doc_type': str, 'raw_content': str}]
    """
    try:
        conn = get_connection()
        conn.row_factory = lambda cursor, row: {
            col[0]: row[idx] for idx, col in enumerate(cursor.description)
        }
        cursor = conn.cursor()
        
        query = """
            SELECT d.id as doc_id, d.filename, d.doc_type, 
                   r.raw_content, r.content_type, r.file_extension
            FROM documents d
            JOIN document_raw_data r ON d.id = r.doc_id
            WHERE d.status = 'active'
        """
        params = []
        
        if doc_type:
            query += " AND d.doc_type = ?"
            params.append(doc_type)
        
        query += " ORDER BY d.id"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        conn.close()
        
        logger.info(f"✅ 取得 {len(results)} 筆 raw data")
        return results
        
    except Exception as e:
        logger.error(f"❌ 取得所有 Raw data 失敗: {e}")
        return []


def has_raw_data(doc_id: int) -> bool:
    """
    檢查文件是否有原始資料
    
    Args:
        doc_id: 文件 ID
    
    Returns:
        bool: 是否有原始資料
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT COUNT(*) FROM document_raw_data WHERE doc_id = ?",
            (doc_id,)
        )
        count = cursor.fetchone()[0]
        
        conn.close()
        return count > 0
        
    except Exception as e:
        logger.error(f"❌ 檢查 Raw data 失敗: {e}")
        return False
