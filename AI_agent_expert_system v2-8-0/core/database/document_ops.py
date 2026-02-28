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
    analysis_mode: str = "auto",
    model_used: str = "gpt-4o-mini",
    **kwargs,
) -> int:
    """
    建立新文件記錄。
    委派給 create_document_enhanced，保留向後相容。
    """
    return create_document_enhanced(
        filename=filename,
        doc_type=doc_type,
        analysis_mode=analysis_mode,
        model_used=model_used,
        **kwargs,
    )


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
                SELECT id, filename, doc_type, upload_date, analysis_mode, model_used,
                       file_size, category, tags, processing_time, file_hash
                FROM documents
                WHERE doc_type = ?
                ORDER BY upload_date DESC
            """, (doc_type,))
        else:
            cursor.execute("""
                SELECT id, filename, doc_type, upload_date, analysis_mode, model_used,
                       file_size, category, tags, processing_time, file_hash
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
        allowed_fields = [
            'filename', 'doc_type', 'analysis_mode', 'model_used',
            'parent_doc_id', 'source_type', 'status',
        ]
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




def create_document_enhanced(
    filename: str,
    doc_type: str,
    analysis_mode: str = "auto",
    model_used: str = "gpt-4o-mini",
    category: Optional[str] = None,
    tags: Optional[str] = None,
    file_size: Optional[int] = None,
    file_hash: Optional[str] = None,
    processing_time: Optional[float] = None,
    author: Optional[str] = None,
    department: Optional[str] = None,
    factory: Optional[str] = None,
    language: str = "zh-TW",
    priority: int = 0,
    summary: Optional[str] = None,
    key_points: Optional[str] = None,
    # Troubleshooting 專用欄位
    product_model: Optional[str] = None,
    defect_code: Optional[str] = None,
    station: Optional[str] = None,
    yield_loss: Optional[str] = None,
    **kwargs
) -> int:
    """
    建立新文件記錄 (增強版,支援更多元數據)
    
    Args:
        filename: 檔案名稱
        doc_type: 文件類型 ('Knowledge', 'Troubleshooting', 'Training')
        analysis_mode: 分析模式 ('text_only', 'vision', 'auto')
        model_used: 使用的模型名稱
        category: 二級分類
        tags: 標籤 (JSON 字串)
        file_size: 檔案大小 (bytes)
        file_hash: 檔案 hash 值
        processing_time: 處理時間 (秒)
        author: 作者/上傳者
        department: 部門
        factory: 工廠
        language: 語言代碼
        priority: 優先級 (0-10)
        summary: 文件摘要
        key_points: 重點摘要 (JSON 字串)
        product_model: 產品型號 (Troubleshooting專用)
        defect_code: 缺陷代碼 (Troubleshooting專用)
        station: 檢出站點 (Troubleshooting專用)
        yield_loss: 產量損失 (Troubleshooting專用)
    
    Returns:
        int: 文件 ID
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 檢查是否已存在相同 hash 的文件
        if file_hash:
            cursor.execute("SELECT id, filename FROM documents WHERE file_hash = ?", (file_hash,))
            existing = cursor.fetchone()
            if existing:
                logger.warning(f"⚠️ 文件已存在: {existing[1]} (ID: {existing[0]})")
                conn.close()
                return existing[0]
        
        cursor.execute("""
            INSERT INTO documents (
                filename, doc_type, analysis_mode, model_used,
                category, tags, file_size, file_hash, processing_time,
                author, department, factory, language, priority,
                summary, key_points, status,
                product_model, defect_code, station, yield_loss
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?)
        """, (
            filename, doc_type, analysis_mode, model_used,
            category, tags, file_size, file_hash, processing_time,
            author, department, factory, language, priority,
            summary, key_points,
            product_model, defect_code, station, yield_loss
        ))
        
        doc_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"✅ 文件已建立 (增強版): {filename} (ID: {doc_id})")
        return doc_id
        
    except Exception as e:
        logger.error(f"❌ 建立文件失敗: {e}")
        raise


def get_document_by_hash(file_hash: str) -> Optional[Dict]:
    """
    根據檔案 hash 取得文件
    
    Args:
        file_hash: 檔案 hash 值
    
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
            SELECT * FROM documents WHERE file_hash = ?
        """, (file_hash,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            logger.debug(f"✅ 已找到文件 (by hash): {result['filename']}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 取得文件失敗: {e}")
        return None


def increment_access_count(doc_id: int) -> bool:
    """
    增加文件訪問次數
    
    Args:
        doc_id: 文件 ID
    
    Returns:
        bool: 是否更新成功
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE documents
            SET access_count = COALESCE(access_count, 0) + 1,
                last_accessed = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (doc_id,))
        
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return updated
        
    except Exception as e:
        logger.error(f"❌ 更新訪問次數失敗: {e}")
        return False


def log_search_history(
    query: str,
    intent: Optional[str] = None,
    strategy: Optional[str] = None,
    result_count: int = 0,
    search_time: float = 0.0,
    result_chunks: Optional[str] = None,
    user_clicked_chunk_id: Optional[int] = None,
    feedback: Optional[str] = None
) -> int:
    """
    記錄搜尋歷史 — 已棄用，請改用 metadata_ops.log_search_analytics。
    此函式僅為向後相容保留，委派至 search_analytics 表。
    """
    from .metadata_ops import log_search_analytics
    return log_search_analytics(
        query=query,
        intent=intent,
        strategy=strategy,
        result_count=result_count,
        search_time_ms=search_time * 1000,
        top_chunk_id=user_clicked_chunk_id,
    )


# get_chunks_by_doc_id 已移至 vector_ops.py — 此處保留向後相容的 re-export
from .vector_ops import get_chunks_by_doc_id  # noqa: F401

