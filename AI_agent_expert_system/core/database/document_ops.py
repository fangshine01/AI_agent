"""
文件操作模組
負責文件的 CRUD 操作
"""

import logging
from typing import Optional, Dict, List
from .connection import get_connection

logger = logging.getLogger(__name__)


def create_document(
    filename: str,
    doc_type: str,
    analysis_mode: str,
    model_used: str
) -> int:
    """
    建立新文件記錄
    
    Args:
        filename: 檔案名稱
        doc_type: 文件類型 ('Knowledge', 'Troubleshooting', 'Training')
        analysis_mode: 分析模式 ('text_only', 'vision', 'auto')
        model_used: 使用的模型名稱
    
    Returns:
        int: 文件 ID
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO documents (filename, doc_type, analysis_mode, model_used)
            VALUES (?, ?, ?, ?)
        """, (filename, doc_type, analysis_mode, model_used))
        
        doc_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"✅ 文件已建立: {filename} (ID: {doc_id})")
        return doc_id
        
    except Exception as e:
        logger.error(f"❌ 建立文件失敗: {e}")
        raise


def get_document(doc_id: int) -> Optional[Dict]:
    """
    取得文件資訊
    
    Args:
        doc_id: 文件 ID
    
    Returns:
        Optional[Dict]: 文件資訊,若不存在則回傳 None
    """
    try:
        conn = get_connection()
        conn.row_factory = lambda cursor, row: {
            col[0]: row[idx] for idx, col in enumerate(cursor.description)
        }
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, filename, doc_type, upload_date, analysis_mode, model_used
            FROM documents WHERE id = ?
        """, (doc_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            logger.debug(f"✅ 已取得文件: {result['filename']}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 取得文件失敗: {e}")
        return None


def get_all_documents(doc_type: Optional[str] = None) -> List[Dict]:
    """
    取得所有文件列表
    
    Args:
        doc_type: 可選,過濾特定類型的文件
    
    Returns:
        List[Dict]: 文件列表
    """
    try:
        conn = get_connection()
        conn.row_factory = lambda cursor, row: {
            col[0]: row[idx] for idx, col in enumerate(cursor.description)
        }
        cursor = conn.cursor()
        
        if doc_type:
            cursor.execute("""
                SELECT id, filename, doc_type, upload_date, analysis_mode, model_used
                FROM documents
                WHERE doc_type = ?
                ORDER BY upload_date DESC
            """, (doc_type,))
        else:
            cursor.execute("""
                SELECT id, filename, doc_type, upload_date, analysis_mode, model_used
                FROM documents
                ORDER BY upload_date DESC
            """)
        
        results = cursor.fetchall()
        conn.close()
        
        logger.debug(f"✅ 已取得 {len(results)} 筆文件")
        return results
        
    except Exception as e:
        logger.error(f"❌ 取得文件列表失敗: {e}")
        return []


def update_document(doc_id: int, **kwargs) -> bool:
    """
    更新文件資訊
    
    Args:
        doc_id: 文件 ID
        **kwargs: 要更新的欄位 (filename, doc_type, analysis_mode, model_used)
    
    Returns:
        bool: 是否更新成功
    """
    try:
        allowed_fields = ['filename', 'doc_type', 'analysis_mode', 'model_used']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            logger.warning("沒有可更新的欄位")
            return False
        
        conn = get_connection()
        cursor = conn.cursor()
        
        set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [doc_id]
        
        cursor.execute(f"""
            UPDATE documents
            SET {set_clause}
            WHERE id = ?
        """, values)
        
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        if updated:
            logger.info(f"✅ 文件已更新: {doc_id}")
        
        return updated
        
    except Exception as e:
        logger.error(f"❌ 更新文件失敗: {e}")
        return False


def delete_document(doc_id: int) -> bool:
    """
    刪除文件 (會自動刪除相關 chunks,因為有 CASCADE)
    
    Args:
        doc_id: 文件 ID
    
    Returns:
        bool: 是否刪除成功
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 先取得文件名稱用於日誌
        cursor.execute("SELECT filename FROM documents WHERE id = ?", (doc_id,))
        result = cursor.fetchone()
        
        if not result:
            logger.warning(f"文件不存在: {doc_id}")
            conn.close()
            return False
        
        filename = result[0]
        
        # 刪除文件 (CASCADE 會自動刪除相關 chunks)
        cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        deleted = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        
        if deleted:
            logger.info(f"✅ 文件已刪除: {filename} (ID: {doc_id})")
        
        return deleted
        
    except Exception as e:
        logger.error(f"❌ 刪除文件失敗: {e}")
        return False


def get_document_stats() -> Dict:
    """
    取得文件統計資訊
    
    Returns:
        Dict: 統計資訊 (總數、各類型數量)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 總數
        cursor.execute("SELECT COUNT(*) FROM documents")
        total = cursor.fetchone()[0]
        
        # 按類型統計
        cursor.execute("""
            SELECT doc_type, COUNT(*) as count
            FROM documents
            GROUP BY doc_type
        """)
        by_type = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
        
        return {
            'total_documents': total,
            'by_type': by_type
        }
        
    except Exception as e:
        logger.error(f"❌ 取得統計失敗: {e}")
        return {'total_documents': 0, 'by_type': {}}


if __name__ == "__main__":
    # 測試文件操作
    print("文件操作模組測試")
    
    try:
        # 建立測試文件
        doc_id = create_document(
            filename="test.pptx",
            doc_type="Knowledge",
            analysis_mode="auto",
            model_used="gpt-4o-mini"
        )
        print(f"✅ 測試文件已建立: {doc_id}")
        
        # 取得文件
        doc = get_document(doc_id)
        print(f"✅ 文件資訊: {doc}")
        
        # 取得統計
        stats = get_document_stats()
        print(f"✅ 統計資訊: {stats}")
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
