"""
Chat History API - 對話歷史管理路由 (v2.2.0)

提供用戶對話歷史的 CRUD 操作：
- 取得 Session 列表
- 取得指定 Session 的對話內容
- 建立新 Session
- 刪除 Session
- 儲存對話訊息

權限控制: 用戶僅能存取自己的 user_id 名下的資料
資料策略: 永久保留 (已確認決策)
"""

import uuid
import sqlite3
import logging
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

import backend.config as cfg

logger = logging.getLogger(__name__)
router = APIRouter()


# ========== 請求/回應模型 ==========

class CreateSessionRequest(BaseModel):
    """建立新 Session"""
    title: Optional[str] = Field(default="新對話", description="對話標題")
    model_used: Optional[str] = Field(default=None, description="使用的模型")


class SessionInfo(BaseModel):
    """Session 資訊"""
    session_id: str
    title: str
    model_used: Optional[str] = None
    message_count: int = 0
    total_tokens: int = 0
    created_at: str
    updated_at: str
    last_activity_at: str


class SessionListResponse(BaseModel):
    """Session 列表回應"""
    success: bool = True
    sessions: List[SessionInfo] = []
    total: int = 0


class ChatMessage(BaseModel):
    """對話訊息"""
    role: str = Field(..., description="角色: user | assistant | system")
    content: str = Field(..., description="訊息內容")
    model_used: Optional[str] = None
    tokens_used: int = 0
    created_at: Optional[str] = None


class SaveMessageRequest(BaseModel):
    """儲存對話訊息"""
    session_id: str = Field(..., description="Session ID")
    role: str = Field(..., description="角色: user | assistant")
    content: str = Field(..., description="訊息內容")
    model_used: Optional[str] = None
    tokens_used: int = 0


class SessionHistoryResponse(BaseModel):
    """Session 歷史回應"""
    success: bool = True
    session_id: str
    title: str = ""
    messages: List[ChatMessage] = []
    total_tokens: int = 0


# ========== 資料庫操作工具 ==========

def _get_db_connection() -> sqlite3.Connection:
    """
    取得獨立的 DB Connection（每個 Request 獨立連線）
    避免多執行緒共用 Connection 導致 locked
    """
    conn = sqlite3.connect(cfg.DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn


def _require_user_id(request: Request) -> str:
    """
    確保 Request 包含有效的 user_id
    若未認證則拋出 401 錯誤
    """
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要先驗證 API Key 才能存取對話歷史"
        )
    return user_id


# ========== API Endpoints ==========

@router.get("/sessions", response_model=SessionListResponse, summary="取得用戶的所有對話 Session")
async def get_sessions(request: Request):
    """
    取得當前用戶的所有對話 Session 列表
    依照最後活動時間排序（最新在前）
    """
    user_id = _require_user_id(request)

    try:
        conn = _get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT session_id, title, model_used, message_count, total_tokens,
                   created_at, updated_at, last_activity_at
            FROM sessions
            WHERE user_id = ?
            ORDER BY last_activity_at DESC
        """, (user_id,))

        rows = cursor.fetchall()
        conn.close()

        sessions = [
            SessionInfo(
                session_id=row["session_id"],
                title=row["title"],
                model_used=row["model_used"],
                message_count=row["message_count"],
                total_tokens=row["total_tokens"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                last_activity_at=row["last_activity_at"],
            )
            for row in rows
        ]

        return SessionListResponse(sessions=sessions, total=len(sessions))

    except Exception as e:
        logger.error(f"[History] 取得 Session 列表失敗: {e}")
        raise HTTPException(status_code=500, detail=f"取得對話列表失敗: {str(e)}")


@router.post("/sessions", summary="建立新的對話 Session")
async def create_session(request: Request, body: CreateSessionRequest):
    """
    建立新的對話 Session
    回傳新的 session_id 供前端使用
    """
    user_id = _require_user_id(request)
    session_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    try:
        conn = _get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO sessions (session_id, user_id, title, model_used, created_at, updated_at, last_activity_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (session_id, user_id, body.title, body.model_used, now, now, now))

        conn.commit()
        conn.close()

        logger.info(f"[History] 新 Session 建立: {session_id}, user={user_id}")

        return {
            "success": True,
            "session_id": session_id,
            "title": body.title,
            "created_at": now,
        }

    except Exception as e:
        logger.error(f"[History] 建立 Session 失敗: {e}")
        raise HTTPException(status_code=500, detail=f"建立對話失敗: {str(e)}")


@router.get("/sessions/{session_id}", response_model=SessionHistoryResponse, summary="取得指定 Session 的對話內容")
async def get_session_history(session_id: str, request: Request):
    """
    取得指定 Session 的完整對話歷史
    僅允許存取自己名下的 Session (安全隔離)
    """
    user_id = _require_user_id(request)

    try:
        conn = _get_db_connection()
        cursor = conn.cursor()

        # 驗證 Session 歸屬權
        cursor.execute(
            "SELECT title, total_tokens FROM sessions WHERE session_id = ? AND user_id = ?",
            (session_id, user_id)
        )
        session_row = cursor.fetchone()

        if not session_row:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="找不到此對話，或該對話不屬於當前用戶"
            )

        # 取得對話內容
        cursor.execute("""
            SELECT role, content, model_used, tokens_used, created_at
            FROM chat_history
            WHERE session_id = ? AND user_id = ?
            ORDER BY created_at ASC
        """, (session_id, user_id))

        rows = cursor.fetchall()
        conn.close()

        messages = [
            ChatMessage(
                role=row["role"],
                content=row["content"],
                model_used=row["model_used"],
                tokens_used=row["tokens_used"] or 0,
                created_at=row["created_at"],
            )
            for row in rows
        ]

        return SessionHistoryResponse(
            session_id=session_id,
            title=session_row["title"],
            messages=messages,
            total_tokens=session_row["total_tokens"] or 0,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[History] 取得 Session 歷史失敗: {e}")
        raise HTTPException(status_code=500, detail=f"取得對話歷史失敗: {str(e)}")


@router.post("/messages", summary="儲存對話訊息")
async def save_message(request: Request, body: SaveMessageRequest):
    """
    儲存一筆對話訊息到 chat_history

    前端每次發送/接收訊息時呼叫此端點，
    自動更新 Session 的統計資料 (message_count, total_tokens)
    """
    user_id = _require_user_id(request)
    now = datetime.utcnow().isoformat()

    try:
        conn = _get_db_connection()
        cursor = conn.cursor()

        # 確認 Session 存在且歸屬正確
        cursor.execute(
            "SELECT session_id FROM sessions WHERE session_id = ? AND user_id = ?",
            (body.session_id, user_id)
        )
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session 不存在或不屬於當前用戶"
            )

        # 寫入對話記錄
        cursor.execute("""
            INSERT INTO chat_history (user_id, session_id, role, content, model_used, tokens_used, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, body.session_id, body.role, body.content, body.model_used, body.tokens_used, now))

        # 更新 Session 統計
        cursor.execute("""
            UPDATE sessions
            SET message_count = message_count + 1,
                total_tokens = total_tokens + ?,
                updated_at = ?,
                last_activity_at = ?
            WHERE session_id = ? AND user_id = ?
        """, (body.tokens_used, now, now, body.session_id, user_id))

        # 如果是第一筆 user 訊息，自動用前 30 字作為標題
        if body.role == "user":
            cursor.execute(
                "SELECT message_count FROM sessions WHERE session_id = ?",
                (body.session_id,)
            )
            row = cursor.fetchone()
            if row and row["message_count"] == 1:
                auto_title = body.content[:30] + ("..." if len(body.content) > 30 else "")
                cursor.execute(
                    "UPDATE sessions SET title = ? WHERE session_id = ?",
                    (auto_title, body.session_id)
                )

        conn.commit()
        conn.close()

        return {"success": True, "message": "訊息已儲存"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[History] 儲存訊息失敗: {e}")
        raise HTTPException(status_code=500, detail=f"儲存訊息失敗: {str(e)}")


@router.delete("/sessions/{session_id}", summary="刪除指定 Session 及其對話記錄")
async def delete_session(session_id: str, request: Request):
    """
    刪除指定 Session 及其所有對話記錄
    僅允許刪除自己名下的 Session
    """
    user_id = _require_user_id(request)

    try:
        conn = _get_db_connection()
        cursor = conn.cursor()

        # 驗證歸屬權
        cursor.execute(
            "SELECT session_id FROM sessions WHERE session_id = ? AND user_id = ?",
            (session_id, user_id)
        )
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="找不到此對話，或該對話不屬於當前用戶"
            )

        # 刪除對話記錄
        cursor.execute(
            "DELETE FROM chat_history WHERE session_id = ? AND user_id = ?",
            (session_id, user_id)
        )

        # 刪除 Session
        cursor.execute(
            "DELETE FROM sessions WHERE session_id = ? AND user_id = ?",
            (session_id, user_id)
        )

        conn.commit()
        conn.close()

        logger.info(f"[History] Session 已刪除: {session_id}, user={user_id}")

        return {"success": True, "message": "對話已刪除"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[History] 刪除 Session 失敗: {e}")
        raise HTTPException(status_code=500, detail=f"刪除對話失敗: {str(e)}")


@router.patch("/sessions/{session_id}/title", summary="更新 Session 標題")
async def update_session_title(session_id: str, request: Request, title: str):
    """
    更新對話 Session 的標題

    Args:
        session_id: Session UUID
        request: HTTP Request（自動從 Header 提取 user_id）
        title: 新的 Session 標題文字

    Returns:
        dict: {"success": True, "message": "標題已更新"}

    Raises:
        HTTPException 404: Session 不存在或不屬於當前用戶
        HTTPException 500: 資料庫更新失敗

    Note:
        僅允許更新自己的 Session（依 BYOK Identity 隔離）
    """
    user_id = _require_user_id(request)

    try:
        conn = _get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE sessions SET title = ?, updated_at = ? WHERE session_id = ? AND user_id = ?",
            (title, datetime.utcnow().isoformat(), session_id, user_id)
        )

        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Session 不存在或不屬於當前用戶")

        conn.commit()
        conn.close()

        return {"success": True, "message": "標題已更新"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[History] 更新標題失敗: {e}")
        raise HTTPException(status_code=500, detail=f"更新標題失敗: {str(e)}")
