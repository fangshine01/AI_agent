"""
Metadata 操作模組
負責 troubleshooting_metadata, procedure_metadata, chunk_metadata 表的操作

版本相關操作已遷移至 version_ops.py
搜尋分析操作已遷移至 analytics_ops.py
"""

import json
import logging
from typing import Optional, Dict, List
from .connection import get_connection

# --- 向後相容：從新模組重新匯出 ---
from .version_ops import create_version, get_document_versions          # noqa: F401
from .analytics_ops import log_search_analytics, update_search_feedback, get_search_stats  # noqa: F401

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
