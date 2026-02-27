"""
GDPR / 資料隱私合規 API (v2.2.0 Phase 2)

提供：
- GET  /user/export   → 導出用戶所有個人資料 (JSON)
- DELETE /user/data   → 刪除用戶所有個人資料
- GET  /user/stats    → 用戶個人統計摘要

權限控制: 透過 IdentityMiddleware 的 user_id 限制存取範圍
"""

import sqlite3
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Query, status
from fastapi.responses import JSONResponse

import backend.config as cfg

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_conn() -> sqlite3.Connection:
    """取得獨立 DB 連線"""
    conn = sqlite3.connect(cfg.DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn


def _require_user(request: Request) -> str:
    """取得已驗證的 user_id"""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要驗證才能存取個人資料"
        )
    return user_id


@router.get("/export", summary="導出個人資料 (GDPR)")
async def export_user_data(request: Request):
    """
    導出用戶的所有個人資料

    包含：
    - 所有對話 Session
    - 所有對話訊息
    - Token 統計摘要

    回傳格式: JSON
    """
    user_id = _require_user(request)

    try:
        conn = _get_conn()
        cursor = conn.cursor()

        # 取得所有 Session
        cursor.execute("""
            SELECT session_id, title, model_used, message_count, total_tokens,
                   created_at, updated_at, last_activity_at
            FROM sessions WHERE user_id = ?
            ORDER BY created_at ASC
        """, (user_id,))
        sessions = [dict(row) for row in cursor.fetchall()]

        # 取得所有對話記錄
        cursor.execute("""
            SELECT session_id, role, content, model_used, tokens_used, created_at
            FROM chat_history WHERE user_id = ?
            ORDER BY created_at ASC
        """, (user_id,))
        messages = [dict(row) for row in cursor.fetchall()]

        # 統計摘要
        cursor.execute("""
            SELECT COUNT(*) as total_messages,
                   COALESCE(SUM(tokens_used), 0) as total_tokens
            FROM chat_history WHERE user_id = ?
        """, (user_id,))
        stats_row = cursor.fetchone()

        conn.close()

        export_data = {
            "export_info": {
                "user_id_hash": user_id,
                "exported_at": datetime.utcnow().isoformat(),
                "data_retention_policy": "永久保留（系統預設）",
            },
            "statistics": {
                "total_sessions": len(sessions),
                "total_messages": stats_row["total_messages"],
                "total_tokens": stats_row["total_tokens"],
            },
            "sessions": sessions,
            "messages": messages,
        }

        logger.info(f"[GDPR] 用戶資料導出: user={user_id}, sessions={len(sessions)}, messages={len(messages)}")

        return export_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[GDPR] 導出失敗: {e}")
        raise HTTPException(status_code=500, detail=f"導出失敗: {str(e)}")


@router.delete("/data", summary="刪除個人資料 (GDPR)")
async def delete_user_data(
    request: Request,
    confirm: bool = Query(False, description="必須設為 true 以確認刪除"),
):
    """
    刪除用戶的所有個人資料

    ⚠️ 此操作不可逆！
    必須傳入 confirm=true 作為二次確認。

    刪除範圍：
    - 所有對話記錄 (chat_history)
    - 所有 Session (sessions)
    """
    user_id = _require_user(request)

    if not confirm:
        return JSONResponse(
            status_code=400,
            content={
                "error": True,
                "message": "請設定 confirm=true 以確認刪除。此操作不可逆！",
            },
        )

    try:
        conn = _get_conn()
        cursor = conn.cursor()

        # 記錄刪除前的統計（合規要求：保留刪除日誌）
        cursor.execute("SELECT COUNT(*) as cnt FROM chat_history WHERE user_id = ?", (user_id,))
        msg_count = cursor.fetchone()["cnt"]
        cursor.execute("SELECT COUNT(*) as cnt FROM sessions WHERE user_id = ?", (user_id,))
        session_count = cursor.fetchone()["cnt"]

        # 執行刪除
        cursor.execute("DELETE FROM chat_history WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()

        # 合規日誌（記錄刪除操作，不含個人資料內容）
        client_ip = request.client.host if request.client else "unknown"
        logger.warning(
            f"[GDPR] 用戶資料已刪除: user={user_id}, "
            f"deleted_sessions={session_count}, deleted_messages={msg_count}, "
            f"request_ip={client_ip}, timestamp={datetime.utcnow().isoformat()}"
        )

        return {
            "success": True,
            "message": "所有個人資料已永久刪除",
            "deleted": {
                "sessions": session_count,
                "messages": msg_count,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[GDPR] 刪除失敗: {e}")
        raise HTTPException(status_code=500, detail=f"刪除失敗: {str(e)}")


@router.get("/stats", summary="個人統計摘要")
async def get_user_stats(request: Request):
    """
    取得用戶的個人統計摘要

    Args:
        request: HTTP Request（自動從 X-User-Identity Header 提取 user_id）

    Returns:
        dict:
            - user_id_hash (str): 用戶身份 Hash（前 16 字元）
            - total_sessions (int): 總對話 Session 數
            - total_messages (int): 總訊息數
            - total_tokens (int): 累計 Token 使用量
            - first_session (str): 首次使用時間 (ISO 格式)
            - last_activity (str): 最後活動時間 (ISO 格式)
            - model_usage (list): 模型使用分佈 [{"model_used", "count", "tokens"}]

    Raises:
        HTTPException 401: 未提供身份識別
        HTTPException 500: 資料庫查詢失敗
    """
    user_id = _require_user(request)

    try:
        conn = _get_conn()
        cursor = conn.cursor()

        # Session 統計
        cursor.execute("""
            SELECT COUNT(*) as total_sessions,
                   COALESCE(SUM(message_count), 0) as total_messages,
                   COALESCE(SUM(total_tokens), 0) as total_tokens,
                   MIN(created_at) as first_session,
                   MAX(last_activity_at) as last_activity
            FROM sessions WHERE user_id = ?
        """, (user_id,))
        row = cursor.fetchone()

        # 模型使用分佈
        cursor.execute("""
            SELECT model_used, COUNT(*) as count, COALESCE(SUM(tokens_used), 0) as tokens
            FROM chat_history
            WHERE user_id = ? AND model_used IS NOT NULL
            GROUP BY model_used
            ORDER BY tokens DESC
        """, (user_id,))
        model_usage = [dict(r) for r in cursor.fetchall()]

        conn.close()

        return {
            "user_id_hash": user_id,
            "total_sessions": row["total_sessions"],
            "total_messages": row["total_messages"],
            "total_tokens": row["total_tokens"],
            "first_session": row["first_session"],
            "last_activity": row["last_activity"],
            "model_usage": model_usage,
        }

    except Exception as e:
        logger.error(f"[GDPR] 取得統計失敗: {e}")
        raise HTTPException(status_code=500, detail=f"取得統計失敗: {str(e)}")
