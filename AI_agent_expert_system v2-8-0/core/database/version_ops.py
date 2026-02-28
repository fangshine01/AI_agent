"""
版本操作模組
負責 document_versions 表的操作
"""

import json
import logging
from typing import Dict, List
from .connection import get_connection

logger = logging.getLogger(__name__)


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
