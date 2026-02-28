"""
Chat History Service — 對話歷史資料庫操作
從 api/v1/history.py 抽離所有 raw sqlite3 操作，集中管理連線與 SQL

所有函式接受 db_path 參數，不直接依賴 config 模組。
"""

import uuid
import sqlite3
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# 連線管理
# ──────────────────────────────────────────────

def _get_conn(db_path: str) -> sqlite3.Connection:
    """取得獨立 DB Connection（每個 request 一條，避免多執行緒 lock）"""
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn


# ──────────────────────────────────────────────
# Session CRUD
# ──────────────────────────────────────────────

def list_sessions(db_path: str, user_id: str) -> List[Dict[str, Any]]:
    """取得指定使用者的所有 Session（依最後活動時間倒序）"""
    conn = _get_conn(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT session_id, title, model_used, message_count, total_tokens,
                   created_at, updated_at, last_activity_at
            FROM sessions
            WHERE user_id = ?
            ORDER BY last_activity_at DESC
        """, (user_id,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def create_session(
    db_path: str,
    user_id: str,
    title: str = "新對話",
    model_used: Optional[str] = None,
) -> Dict[str, Any]:
    """建立新 Session，回傳包含 session_id / title / created_at 的 dict"""
    session_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    conn = _get_conn(db_path)
    try:
        conn.execute("""
            INSERT INTO sessions
                (session_id, user_id, title, model_used, created_at, updated_at, last_activity_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (session_id, user_id, title, model_used, now, now, now))
        conn.commit()
        logger.info(f"[History] 新 Session 建立: {session_id}, user={user_id}")
        return {"session_id": session_id, "title": title, "created_at": now}
    finally:
        conn.close()


def get_session_history(
    db_path: str, session_id: str, user_id: str
) -> Optional[Dict[str, Any]]:
    """
    取得單一 Session 的對話歷史。
    回傳 None 表示 session 不存在或不屬於該使用者。
    """
    conn = _get_conn(db_path)
    try:
        cursor = conn.cursor()

        # 驗證 Session 歸屬權
        cursor.execute(
            "SELECT title, total_tokens FROM sessions WHERE session_id = ? AND user_id = ?",
            (session_id, user_id),
        )
        session_row = cursor.fetchone()
        if not session_row:
            return None

        # 取得對話內容
        cursor.execute("""
            SELECT role, content, model_used, tokens_used, created_at
            FROM chat_history
            WHERE session_id = ? AND user_id = ?
            ORDER BY created_at ASC
        """, (session_id, user_id))

        messages = [
            {
                "role": row["role"],
                "content": row["content"],
                "model_used": row["model_used"],
                "tokens_used": row["tokens_used"] or 0,
                "created_at": row["created_at"],
            }
            for row in cursor.fetchall()
        ]

        return {
            "session_id": session_id,
            "title": session_row["title"],
            "messages": messages,
            "total_tokens": session_row["total_tokens"] or 0,
        }
    finally:
        conn.close()


def delete_session(db_path: str, session_id: str, user_id: str) -> bool:
    """
    刪除 Session 及其所有對話記錄。
    回傳 True 表示已刪除；False 表示 session 不存在 / 不屬於使用者。
    """
    conn = _get_conn(db_path)
    try:
        cursor = conn.cursor()

        # 驗證歸屬權
        cursor.execute(
            "SELECT session_id FROM sessions WHERE session_id = ? AND user_id = ?",
            (session_id, user_id),
        )
        if not cursor.fetchone():
            return False

        cursor.execute(
            "DELETE FROM chat_history WHERE session_id = ? AND user_id = ?",
            (session_id, user_id),
        )
        cursor.execute(
            "DELETE FROM sessions WHERE session_id = ? AND user_id = ?",
            (session_id, user_id),
        )
        conn.commit()
        logger.info(f"[History] Session 已刪除: {session_id}, user={user_id}")
        return True
    finally:
        conn.close()


def update_session_title(
    db_path: str, session_id: str, user_id: str, title: str
) -> bool:
    """更新 Session 標題。回傳 True 表示成功更新。"""
    conn = _get_conn(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE sessions SET title = ?, updated_at = ? WHERE session_id = ? AND user_id = ?",
            (title, datetime.utcnow().isoformat(), session_id, user_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


# ──────────────────────────────────────────────
# 訊息操作
# ──────────────────────────────────────────────

def save_message(
    db_path: str,
    user_id: str,
    session_id: str,
    role: str,
    content: str,
    model_used: Optional[str] = None,
    tokens_used: int = 0,
) -> bool:
    """
    儲存一筆對話訊息，同時更新 Session 統計。
    第一筆 user 訊息會自動以前 30 字設為標題。
    回傳 False 表示 session 不存在 / 不屬於使用者。
    """
    now = datetime.utcnow().isoformat()
    conn = _get_conn(db_path)
    try:
        cursor = conn.cursor()

        # 確認 Session 存在且歸屬正確
        cursor.execute(
            "SELECT session_id FROM sessions WHERE session_id = ? AND user_id = ?",
            (session_id, user_id),
        )
        if not cursor.fetchone():
            return False

        # 寫入對話記錄
        cursor.execute("""
            INSERT INTO chat_history
                (user_id, session_id, role, content, model_used, tokens_used, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, session_id, role, content, model_used, tokens_used, now))

        # 更新 Session 統計
        cursor.execute("""
            UPDATE sessions
            SET message_count = message_count + 1,
                total_tokens = total_tokens + ?,
                updated_at = ?,
                last_activity_at = ?
            WHERE session_id = ? AND user_id = ?
        """, (tokens_used, now, now, session_id, user_id))

        # 如果是第一筆 user 訊息，自動用前 30 字作為標題
        if role == "user":
            cursor.execute(
                "SELECT message_count FROM sessions WHERE session_id = ?",
                (session_id,),
            )
            row = cursor.fetchone()
            if row and row["message_count"] == 1:
                auto_title = content[:30] + ("..." if len(content) > 30 else "")
                cursor.execute(
                    "UPDATE sessions SET title = ? WHERE session_id = ?",
                    (auto_title, session_id),
                )

        conn.commit()
        return True
    finally:
        conn.close()
