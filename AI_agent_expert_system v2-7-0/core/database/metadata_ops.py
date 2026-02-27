"""
Metadata 操作模組
負責 troubleshooting_metadata, procedure_metadata, 
document_versions, search_analytics, chunk_metadata 表的操作
"""

import json
import logging
from typing import Optional, Dict, List
from .connection import get_connection

logger = logging.getLogger(__name__)


# ========== Troubleshooting Metadata ==========

def save_troubleshooting_metadata(
    doc_id: int,
    product_model: str = None,
    defect_code: str = None,
    station: str = None,
    yield_loss: str = None,
    severity: str = None,
    occurrence_date: str = None,
    resolution_date: str = None,
    responsible_dept: str = None,
    status: str = 'active'
) -> bool:
    """儲存 Troubleshooting 專屬 metadata"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO troubleshooting_metadata
                (doc_id, product_model, defect_code, station, yield_loss,
                 severity, occurrence_date, resolution_date, responsible_dept, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (doc_id, product_model, defect_code, station, yield_loss,
              severity, occurrence_date, resolution_date, responsible_dept, status))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Troubleshooting metadata 已儲存 (doc_id: {doc_id})")
        return True
        
    except Exception as e:
        logger.error(f"❌ 儲存 Troubleshooting metadata 失敗: {e}")
        return False


def get_troubleshooting_metadata(doc_id: int) -> Optional[Dict]:
    """取得 Troubleshooting 專屬 metadata"""
    try:
        conn = get_connection()
        conn.row_factory = lambda cursor, row: {
            col[0]: row[idx] for idx, col in enumerate(cursor.description)
        }
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM troubleshooting_metadata WHERE doc_id = ?", (doc_id,))
        result = cursor.fetchone()
        
        conn.close()
        return result
        
    except Exception as e:
        logger.error(f"❌ 取得 Troubleshooting metadata 失敗: {e}")
        return None


def search_troubleshooting(product_model: str = None, defect_code: str = None, 
                           station: str = None) -> List[Dict]:
    """
    搜尋 Troubleshooting 文件 (支援精準匹配)
    
    Args:
        product_model: 產品型號
        defect_code: 缺陷代碼
        station: 檢出站點
    
    Returns:
        List[Dict]: 匹配的文件列表 (含 metadata)
    """
    try:
        conn = get_connection()
        conn.row_factory = lambda cursor, row: {
            col[0]: row[idx] for idx, col in enumerate(cursor.description)
        }
        cursor = conn.cursor()
        
        query = """
            SELECT d.id as doc_id, d.filename, d.doc_type, d.upload_date,
                   t.product_model, t.defect_code, t.station, t.yield_loss,
                   t.severity, t.status
            FROM documents d
            JOIN troubleshooting_metadata t ON d.id = t.doc_id
            WHERE d.doc_type = 'Troubleshooting'
        """
        params = []
        
        if product_model:
            query += " AND t.product_model LIKE ?"
            params.append(f"%{product_model}%")
        
        if defect_code:
            query += " AND t.defect_code LIKE ?"
            params.append(f"%{defect_code}%")
        
        if station:
            query += " AND t.station LIKE ?"
            params.append(f"%{station}%")
        
        query += " ORDER BY d.upload_date DESC"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        conn.close()
        
        logger.debug(f"✅ Troubleshooting 搜尋完成, 找到 {len(results)} 筆")
        return results
        
    except Exception as e:
        logger.error(f"❌ Troubleshooting 搜尋失敗: {e}")
        return []


# ========== Procedure Metadata ==========

def save_procedure_metadata(
    doc_id: int,
    procedure_type: str = None,
    applicable_station: str = None,
    applicable_product: str = None,
    revision: str = None,
    approval_status: str = None,
    approved_by: str = None,
    approved_date: str = None,
    effective_date: str = None,
    expiry_date: str = None
) -> bool:
    """儲存 Procedure 專屬 metadata"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO procedure_metadata
                (doc_id, procedure_type, applicable_station, applicable_product,
                 revision, approval_status, approved_by, approved_date,
                 effective_date, expiry_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (doc_id, procedure_type, applicable_station, applicable_product,
              revision, approval_status, approved_by, approved_date,
              effective_date, expiry_date))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Procedure metadata 已儲存 (doc_id: {doc_id})")
        return True
        
    except Exception as e:
        logger.error(f"❌ 儲存 Procedure metadata 失敗: {e}")
        return False


def get_procedure_metadata(doc_id: int) -> Optional[Dict]:
    """取得 Procedure 專屬 metadata"""
    try:
        conn = get_connection()
        conn.row_factory = lambda cursor, row: {
            col[0]: row[idx] for idx, col in enumerate(cursor.description)
        }
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM procedure_metadata WHERE doc_id = ?", (doc_id,))
        result = cursor.fetchone()
        
        conn.close()
        return result
        
    except Exception as e:
        logger.error(f"❌ 取得 Procedure metadata 失敗: {e}")
        return None


# ========== Document Versions ==========

def create_version(doc_id: int, change_type: str, changed_by: str = None,
                   change_description: str = None, snapshot: Dict = None) -> int:
    """
    建立文件版本記錄
    
    Args:
        doc_id: 文件 ID
        change_type: 'create', 'update', 'reprocess', 'delete'
        changed_by: 操作者
        change_description: 變更描述
        snapshot: 該版本的 metadata 快照
    
    Returns:
        int: 版本號
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 取得目前最新版本號
        cursor.execute(
            "SELECT COALESCE(MAX(version), 0) FROM document_versions WHERE doc_id = ?",
            (doc_id,)
        )
        current_version = cursor.fetchone()[0]
        new_version = current_version + 1
        
        snapshot_json = json.dumps(snapshot, ensure_ascii=False) if snapshot else None
        
        cursor.execute("""
            INSERT INTO document_versions 
                (doc_id, version, change_type, changed_by, change_description, snapshot)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (doc_id, new_version, change_type, changed_by, change_description, snapshot_json))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ 版本記錄已建立: doc_id={doc_id}, version={new_version}")
        return new_version
        
    except Exception as e:
        logger.error(f"❌ 建立版本記錄失敗: {e}")
        return 0


def get_document_versions(doc_id: int) -> List[Dict]:
    """取得文件的所有版本記錄"""
    try:
        conn = get_connection()
        conn.row_factory = lambda cursor, row: {
            col[0]: row[idx] for idx, col in enumerate(cursor.description)
        }
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM document_versions 
            WHERE doc_id = ? 
            ORDER BY version DESC
        """, (doc_id,))
        
        results = cursor.fetchall()
        conn.close()
        return results
        
    except Exception as e:
        logger.error(f"❌ 取得版本記錄失敗: {e}")
        return []


# ========== Search Analytics ==========

def log_search_analytics(
    query: str,
    intent: str = None,
    strategy: str = None,
    result_count: int = 0,
    search_time_ms: float = 0.0,
    top_chunk_id: int = None,
    session_id: str = None,
    user_id: str = None
) -> int:
    """記錄搜尋分析資料"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO search_analytics
                (query, intent, strategy, result_count, search_time_ms,
                 top_chunk_id, session_id, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (query, intent, strategy, result_count, search_time_ms,
              top_chunk_id, session_id, user_id))
        
        record_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.debug(f"📊 搜尋分析已記錄: {query[:50]}")
        return record_id
        
    except Exception as e:
        logger.warning(f"⚠️ 記錄搜尋分析失敗: {e}")
        return 0


def update_search_feedback(record_id: int, user_rating: int = None,
                           feedback: str = None, user_clicked_chunk_id: int = None) -> bool:
    """更新搜尋回饋"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if user_rating is not None:
            updates.append("user_rating = ?")
            params.append(user_rating)
        if feedback is not None:
            updates.append("feedback = ?")
            params.append(feedback)
        if user_clicked_chunk_id is not None:
            updates.append("user_clicked_chunk_id = ?")
            params.append(user_clicked_chunk_id)
        
        if not updates:
            return False
        
        params.append(record_id)
        cursor.execute(f"""
            UPDATE search_analytics 
            SET {', '.join(updates)}
            WHERE id = ?
        """, params)
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ 更新搜尋回饋失敗: {e}")
        return False


def get_search_stats(days: int = 30) -> Dict:
    """取得搜尋統計 (最近 N 天)"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 總搜尋次數
        cursor.execute("""
            SELECT COUNT(*), AVG(search_time_ms), AVG(result_count)
            FROM search_analytics
            WHERE created_at >= datetime('now', ?)
        """, (f'-{days} days',))
        row = cursor.fetchone()
        
        # 意圖分佈
        cursor.execute("""
            SELECT intent, COUNT(*) as count
            FROM search_analytics
            WHERE created_at >= datetime('now', ?) AND intent IS NOT NULL
            GROUP BY intent
            ORDER BY count DESC
        """, (f'-{days} days',))
        intent_dist = {r[0]: r[1] for r in cursor.fetchall()}
        
        # 熱門查詢
        cursor.execute("""
            SELECT query, COUNT(*) as count
            FROM search_analytics
            WHERE created_at >= datetime('now', ?)
            GROUP BY query
            ORDER BY count DESC
            LIMIT 10
        """, (f'-{days} days',))
        top_queries = [{'query': r[0], 'count': r[1]} for r in cursor.fetchall()]
        
        conn.close()
        
        return {
            'total_searches': row[0] or 0,
            'avg_search_time_ms': round(row[1] or 0, 2),
            'avg_result_count': round(row[2] or 0, 1),
            'intent_distribution': intent_dist,
            'top_queries': top_queries
        }
        
    except Exception as e:
        logger.error(f"❌ 取得搜尋統計失敗: {e}")
        return {}


# ========== Chunk Metadata ==========

def save_chunk_metadata(chunk_id: int, metadata: Dict) -> bool:
    """
    儲存 Chunk 結構化 metadata
    
    Args:
        chunk_id: Chunk ID
        metadata: 結構化 metadata (會被存為 JSON)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        metadata_json = json.dumps(metadata, ensure_ascii=False)
        
        cursor.execute("""
            INSERT OR REPLACE INTO chunk_metadata (chunk_id, metadata) 
            VALUES (?, ?)
        """, (chunk_id, metadata_json))
        
        conn.commit()
        conn.close()
        
        logger.debug(f"✅ Chunk metadata 已儲存 (chunk_id: {chunk_id})")
        return True
        
    except Exception as e:
        logger.error(f"❌ 儲存 Chunk metadata 失敗: {e}")
        return False


def get_chunk_metadata(chunk_id: int) -> Optional[Dict]:
    """取得 Chunk 結構化 metadata"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT metadata FROM chunk_metadata WHERE chunk_id = ?", (chunk_id,))
        result = cursor.fetchone()
        
        conn.close()
        
        if result and result[0]:
            return json.loads(result[0])
        return None
        
    except Exception as e:
        logger.error(f"❌ 取得 Chunk metadata 失敗: {e}")
        return None
