"""
Session 管理器 (v2.2.0 Phase 2)

管理用戶 Session 的生命週期：
- Session 建立與驗證
- TTL 自動過期（預設 24 小時，最長 7 天）
- Session 刷新機制
- 過期 Session 清理

配置來源: backend/config.py
  - SESSION_TTL: 預設存活時間（秒）
  - SESSION_MAX_TTL: 最長存活時間（秒）
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List

import backend.config as cfg

logger = logging.getLogger(__name__)


def _get_conn() -> sqlite3.Connection:
    """取得 DB 連線（每次獨立連線）"""
    conn = sqlite3.connect(cfg.DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn


def is_session_valid(session_id: str, user_id: str) -> bool:
    """
    檢查 Session 是否有效（未過期且歸屬正確）

    規則：
    - Session 必須屬於該 user_id
    - last_activity_at 距今不超過 SESSION_TTL
    - created_at 距今不超過 SESSION_MAX_TTL
    """
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT created_at, last_activity_at FROM sessions WHERE session_id = ? AND user_id = ?",
            (session_id, user_id),
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return False

        now = datetime.utcnow()

        # 檢查 TTL（最後活動距今）
        last_activity = datetime.fromisoformat(row["last_activity_at"])
        if (now - last_activity).total_seconds() > cfg.SESSION_TTL:
            logger.info(f"[Session] Session {session_id[:8]}... 已過期 (TTL)")
            return False

        # 檢查 MAX_TTL（建立距今）
        created = datetime.fromisoformat(row["created_at"])
        if (now - created).total_seconds() > cfg.SESSION_MAX_TTL:
            logger.info(f"[Session] Session {session_id[:8]}... 已過期 (MAX_TTL)")
            return False

        return True
    except Exception as e:
        logger.error(f"[Session] 驗證失敗: {e}")
        return False


def refresh_session(session_id: str, user_id: str) -> bool:
    """
    刷新 Session 的最後活動時間

    每次 API 呼叫時自動呼叫此函式，延長 Session 存活
    （但不會超過 SESSION_MAX_TTL）
    """
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()

        cursor.execute(
            "UPDATE sessions SET last_activity_at = ?, updated_at = ? WHERE session_id = ? AND user_id = ?",
            (now, now, session_id, user_id),
        )
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated
    except Exception as e:
        logger.error(f"[Session] 刷新失敗: {e}")
        return False


def cleanup_expired_sessions() -> Dict[str, int]:
    """
    清理過期的 Session 與其對話記錄

    清理條件：
    1. last_activity_at 距今超過 SESSION_TTL
    2. created_at 距今超過 SESSION_MAX_TTL

    注意：Chat History 永久保留（已確認決策），
    此處僅清理 sessions 表中的過期記錄，
    chat_history 表不受影響。

    Returns:
        dict: {"expired_sessions": 清理數量}
    """
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        now = datetime.utcnow()

        # 計算過期時間點
        ttl_cutoff = (now - timedelta(seconds=cfg.SESSION_TTL)).isoformat()
        max_ttl_cutoff = (now - timedelta(seconds=cfg.SESSION_MAX_TTL)).isoformat()

        # 找出過期 Session
        cursor.execute("""
            SELECT session_id FROM sessions
            WHERE last_activity_at < ? OR created_at < ?
        """, (ttl_cutoff, max_ttl_cutoff))

        expired_ids = [row["session_id"] for row in cursor.fetchall()]

        if expired_ids:
            # 標記為過期（不刪除 chat_history，因為永久保留）
            placeholders = ",".join("?" * len(expired_ids))
            cursor.execute(
                f"DELETE FROM sessions WHERE session_id IN ({placeholders})",
                expired_ids,
            )
            conn.commit()

        conn.close()

        count = len(expired_ids)
        if count > 0:
            logger.info(f"[Session] 已清理 {count} 個過期 Session")

        return {"expired_sessions": count}

    except Exception as e:
        logger.error(f"[Session] 清理失敗: {e}")
        return {"expired_sessions": 0, "error": str(e)}


def get_active_session_count() -> int:
    """取得目前活躍的 Session 數量（供監控使用）"""
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        now = datetime.utcnow()
        ttl_cutoff = (now - timedelta(seconds=cfg.SESSION_TTL)).isoformat()

        cursor.execute(
            "SELECT COUNT(*) as cnt FROM sessions WHERE last_activity_at >= ?",
            (ttl_cutoff,),
        )
        row = cursor.fetchone()
        conn.close()
        return row["cnt"] if row else 0
    except Exception as e:
        logger.error(f"[Session] 計算活躍 Session 失敗: {e}")
        return 0


def get_active_user_count() -> int:
    """取得目前不重複的活躍用戶數（供監控使用）"""
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        now = datetime.utcnow()
        ttl_cutoff = (now - timedelta(seconds=cfg.SESSION_TTL)).isoformat()

        cursor.execute(
            "SELECT COUNT(DISTINCT user_id) as cnt FROM sessions WHERE last_activity_at >= ?",
            (ttl_cutoff,),
        )
        row = cursor.fetchone()
        conn.close()
        return row["cnt"] if row else 0
    except Exception as e:
        logger.error(f"[Session] 計算活躍用戶失敗: {e}")
        return 0
