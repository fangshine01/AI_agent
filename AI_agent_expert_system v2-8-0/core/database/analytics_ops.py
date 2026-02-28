"""
搜尋分析操作模組
負責 search_analytics 表的操作
"""

import logging
from typing import Optional, Dict, List
from .connection import get_connection

logger = logging.getLogger(__name__)


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
