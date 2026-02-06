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
    source_type: Optional[str] = None
) -> List[Dict]:
    """
    使用向量相似度搜尋
    
    Args:
        query_embedding: 查詢向量
        top_k: 回傳前 k 筆結果
        source_type: 可選,過濾特定類型的切片
    
    Returns:
        List[Dict]: 搜尋結果,包含 chunk_id, doc_id, source_title, content, similarity
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 將查詢向量轉為 BLOB
        embedding_blob = struct.pack(f'{len(query_embedding)}f', *query_embedding)
        
        # 建立查詢語句
        query = """
            SELECT 
                chunk_id,
                doc_id,
                source_type,
                source_title,
                text_content,
                vec_distance_cosine(embedding, vec_f32(?)) as distance
            FROM vec_chunks
            WHERE embedding IS NOT NULL
        """
        
        params = [embedding_blob]
        
        # 如果指定了 source_type,加入過濾條件
        if source_type:
            query += " AND source_type = ?"
            params.append(source_type)
        
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
                'similarity': 1 - row[5]  # 轉為相似度 (越大越好)
            })
        
        conn.close()
        logger.debug(f"✅ 向量搜尋完成,找到 {len(results)} 筆結果")
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
