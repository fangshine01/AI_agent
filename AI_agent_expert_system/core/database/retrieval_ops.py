"""
檢索操作模組
負責高階文件檢索邏輯 (Metadata Search, Hybrid Search)
"""

import logging
from typing import Dict, Optional, List
from .connection import get_connection

logger = logging.getLogger(__name__)


def find_document_by_metadata(product_model: str, defect_code: str, doc_type: str = 'Troubleshooting') -> Optional[Dict]:
    """
    根據 metadata 精確查找單一文件 (用於 Troubleshooting 智慧路由)
    
    Args:
        product_model: 產品型號 (精確匹配)
        defect_code: 缺陷代碼 (精確匹配)
        doc_type: 文件類型預設為 Troubleshooting
        
    Returns:
        Optional[Dict]: 若找到唯一匹配的文件，回傳其詳細資訊 (包含 content)；否則回傳 None
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. 先從 document_keywords 表查找符合 product 和 defect 的 doc_id
        # ps: 這是最快的方法，因為 ingestion 時已經建立了關鍵字索引
        # 但是 keyword 可能是多對多，所以還需要 join documents 確認類型
        
        # 查詢邏輯:
        # 尋找一份文件，其 keywords 同時包含 product_model (Category: 產品) 和 defect_code (Category: Defect Code)
        # 並且 doc_type 符合
        
        # 簡化策略: 直接查 documents 表的 JSON metadata (如果有的話) 
        # 但目前 metadata 散落在不同表。
        # v5.0 架構中，Troubleshooting metadata 存在 `document_troubleshooting` 表
        
        query = """
            SELECT 
                d.id, d.filename, d.doc_type, 
                t.product_model, t.defect_code, t.station, t.yield_loss,
                rd.raw_content
            FROM documents d
            JOIN troubleshooting_metadata t ON d.id = t.doc_id
            JOIN document_raw_data rd ON d.id = rd.doc_id
            WHERE d.doc_type = ?
            AND t.product_model LIKE ?
            AND t.defect_code LIKE ?
            LIMIT 1
        """
        
        # 使用 LIKE 進行不區分大小寫的匹配，並允許部分模糊 (例如使用者輸入 N706，資料庫存 N706)
        # 改進: 使用 % 進行模糊匹配可能會撈到不相干的，這裡我們先嘗試精確匹配 (IGNORE CASE)
        
        cursor.execute(query, (doc_type, product_model, defect_code))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            logger.info(f"🎯 精確檢索命中: {row[1]} (ID: {row[0]})")
            return {
                'doc_id': row[0],
                'filename': row[1],
                'doc_type': row[2],
                'metadata': {
                    'product_model': row[3],
                    'defect_code': row[4],
                    'station': row[5],
                    'yield_loss': row[6]
                },
                'content': row[7]  # 完整 Raw Content
            }
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Metadata 檢索失敗: {e}")
        return None
