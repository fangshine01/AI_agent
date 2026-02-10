"""
向量操作模組
負責向量資料的存入與查詢
"""

import struct
import logging
from typing import List, Dict, Optional
from .connection import get_connection

logger = logging.getLogger(__name__)


def save_chunk_embedding(
    doc_id: int,
    source_type: str,
    title: str,
    content: str,
    embedding: List[float],
    keywords: Optional[str] = None
) -> int:
    """
    儲存單一切片與其向量
    
    Args:
        doc_id: 文件 ID
        source_type: 來源類型 ('chapter', 'step', 'field', 'section')
        title: 切片標題
        content: 文字內容
        embedding: 向量值 (List[float])
        keywords: 關鍵字 (可選)
    
    Returns:
        int: 切片 ID (chunk_id)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 將向量轉為 BLOB 格式
        embedding_blob = struct.pack(f'{len(embedding)}f', *embedding)
        
        cursor.execute("""
            INSERT INTO vec_chunks (doc_id, source_type, source_title, text_content, embedding, keywords)
            VALUES (?, ?, ?, ?, vec_f32(?), ?)
        """, (doc_id, source_type, title, content, embedding_blob, keywords))
        
        chunk_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.debug(f"✅ 切片已儲存: {title} (ID: {chunk_id})")
        return chunk_id
        
    except Exception as e:
        logger.error(f"❌ 儲存切片失敗: {e}")
        raise


def search_by_vector(
    query_embedding: List[float],
    top_k: int = 5,
    source_type: Optional[str] = None,
    filters: Optional[Dict] = None
) -> List[Dict]:
    """
    使用向量相似度搜尋 (支援 SQL 過濾)
    
    Args:
        query_embedding: 查詢向量
        top_k: 回傳前 k 筆結果
        source_type: 可選,過濾特定類型的切片
        filters: 結構化過濾條件 (doc_type, product, station, topic)
    
    Returns:
        List[Dict]: 搜尋結果
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 將查詢向量轉為 BLOB
        embedding_blob = struct.pack(f'{len(query_embedding)}f', *query_embedding)
        
        # 基本查詢 (JOIN documents 以支援 metadata 過濾)
        query = """
            SELECT 
                v.chunk_id,
                v.doc_id,
                v.source_type,
                v.source_title,
                v.text_content,
                vec_distance_cosine(v.embedding, vec_f32(?)) as distance,
                d.filename,
                d.doc_type
            FROM vec_chunks v
            JOIN documents d ON v.doc_id = d.id
            WHERE v.embedding IS NOT NULL
        """
        
        params = [embedding_blob]
        
        # 1. Source Type 過濾 (原有邏輯)
        if source_type:
            query += " AND v.source_type = ?"
            params.append(source_type)
            
        # 2. 結構化 Filters 過濾
        if filters:
            # Doc Type
            if filters.get('doc_type'):
                query += " AND d.doc_type = ?"
                params.append(filters['doc_type'])
                
            # Product (搜尋檔名或關鍵字)
            if filters.get('product'):
                prod = f"%{filters['product']}%"
                query += " AND (d.filename LIKE ? OR v.keywords LIKE ?)"
                params.extend([prod, prod])
                
            # Station (搜尋檔名, 關鍵字, 或標題)
            if filters.get('station'):
                station = f"%{filters['station']}%"
                query += " AND (d.filename LIKE ? OR v.keywords LIKE ? OR v.source_title LIKE ?)"
                params.extend([station, station, station])
                
            # Topic (搜尋關鍵字)
            if filters.get('topic'):
                topic = f"%{filters['topic']}%"
                query += " AND (v.keywords LIKE ? OR v.source_title LIKE ?)"
                params.extend([topic, topic])

        query += " ORDER BY distance ASC LIMIT ?"
        params.append(top_k)
        
        cursor.execute(query, params)
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'chunk_id': row[0],
                'doc_id': row[1],
                'source_type': row[2],
                'source_title': row[3],
                'content': row[4],
                'similarity': 1 - row[5],
                'document': {
                    'filename': row[6],
                    'doc_type': row[7]
                }
            })
        
        conn.close()
        logger.debug(f"✅ 向量搜尋完成 (Filters: {filters}), 找到 {len(results)} 筆結果")
        return results
        
    except Exception as e:
        logger.error(f"❌ 向量搜尋失敗: {e}")
        return []


def get_chunks_by_doc_id(doc_id: int) -> List[Dict]:
    """
    取得特定文件的所有切片
    
    Args:
        doc_id: 文件 ID
    
    Returns:
        List[Dict]: 切片列表
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT chunk_id, source_type, source_title, text_content, created_at
            FROM vec_chunks
            WHERE doc_id = ?
            ORDER BY chunk_id
        """, (doc_id,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'chunk_id': row[0],
                'source_type': row[1],
                'source_title': row[2],
                'content': row[3],
                'created_at': row[4]
            })
        
        conn.close()
        return results
        
    except Exception as e:
        logger.error(f"❌ 取得切片失敗: {e}")
        return []


def delete_chunks_by_doc_id(doc_id: int) -> int:
    """
    刪除特定文件的所有切片
    
    Args:
        doc_id: 文件 ID
    
    Returns:
        int: 刪除的切片數量
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM vec_chunks WHERE doc_id = ?", (doc_id,))
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ 已刪除 {deleted_count} 個切片 (doc_id: {doc_id})")
        return deleted_count
        
    except Exception as e:
        logger.error(f"❌ 刪除切片失敗: {e}")
        return 0


def update_chunk_keywords(chunk_id: int, keywords: str) -> bool:
    """
    更新切片的關鍵字
    
    Args:
        chunk_id: 切片 ID
        keywords: 關鍵字字串 (JSON or 逗號分隔)
        
    Returns:
        bool: 是否成功
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("UPDATE vec_chunks SET keywords = ? WHERE chunk_id = ?", (keywords, chunk_id))
        
        conn.commit()
        conn.close()
        
        logger.debug(f"✅ 更新切片關鍵字成功 (ID: {chunk_id})")
        return True
        
    except Exception as e:
        logger.error(f"❌ 更新切片關鍵字失敗: {e}")
        return False
        


def get_chunk_content(chunk_id: int) -> Optional[str]:
    """
    取得特定切片的文字內容
    
    Args:
        chunk_id: 切片 ID
        
    Returns:
        str: 文字內容,若找不到則回傳 None
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT text_content FROM vec_chunks WHERE chunk_id = ?", (chunk_id,))
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            return result[0]
        return None
        
    except Exception as e:
        logger.error(f"❌ 取得切片內容失敗: {e}")
        return None


if __name__ == "__main__":
    # 測試向量操作
    print("向量操作模組測試")
    
    # 建立假向量測試
    dummy_embedding = [0.1] * 1536
    
    try:
        chunk_id = save_chunk_embedding(
            doc_id=1,
            source_type="chapter",
            title="測試章節",
            content="這是測試內容",
            embedding=dummy_embedding
        )
        print(f"✅ 測試切片已儲存: {chunk_id}")
        
        # 測試搜尋
        results = search_by_vector(dummy_embedding, top_k=1)
        print(f"✅ 測試搜尋完成: 找到 {len(results)} 筆結果")
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
