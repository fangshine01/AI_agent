"""
Chat History API - 對話歷史管理路由 (v2.7.0)

提供用戶對話歷史的 CRUD 操作。
所有資料庫操作已抽離至 services/history_service.py，
Pydantic 模型定義於 schemas/history.py。

權限控制: 用戶僅能存取自己的 user_id 名下的資料
資料策略: 永久保留 (已確認決策)
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

import backend.config as cfg
from backend.app.schemas.history import (
    CreateSessionRequest,
    SaveMessageRequest,
    SessionHistoryResponse,
    SessionInfo,
    SessionListResponse,
)
from backend.app.services.history_service import (
    create_session as svc_create_session,
    delete_session as svc_delete_session,
    get_session_history as svc_get_history,
    list_sessions as svc_list_sessions,
    save_message as svc_save_message,
    update_session_title as svc_update_title,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ========== 共用依賴 ==========

def _require_user_id(request: Request) -> str:
    """確保 Request 包含有效的 user_id，否則拋出 401"""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要先驗證 API Key 才能存取對話歷史",
        )
    return user_id


# ========== API Endpoints ==========

@router.get("/sessions", response_model=SessionListResponse, summary="取得用戶的所有對話 Session")
async def get_sessions(request: Request):
    """取得當前用戶的所有對話 Session 列表（依最後活動時間排序）"""
    user_id = _require_user_id(request)
    try:
        rows = svc_list_sessions(cfg.DB_PATH, user_id)
        sessions = [SessionInfo(**r) for r in rows]
        return SessionListResponse(sessions=sessions, total=len(sessions))
    except Exception as e:
        logger.error(f"[History] 取得 Session 列表失敗: {e}")
        raise HTTPException(status_code=500, detail=f"取得對話列表失敗: {str(e)}")


@router.post("/sessions", summary="建立新的對話 Session")
async def create_session(request: Request, body: CreateSessionRequest):
    """建立新的對話 Session，回傳 session_id 供前端使用"""
    user_id = _require_user_id(request)
    try:
        result = svc_create_session(cfg.DB_PATH, user_id, body.title, body.model_used)
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"[History] 建立 Session 失敗: {e}")
        raise HTTPException(status_code=500, detail=f"建立對話失敗: {str(e)}")


@router.get(
    "/sessions/{session_id}",
    response_model=SessionHistoryResponse,
    summary="取得指定 Session 的對話內容",
)
async def get_session_history(session_id: str, request: Request):
    """取得指定 Session 的完整對話歷史（僅限自己名下的 Session）"""
    user_id = _require_user_id(request)
    try:
        data = svc_get_history(cfg.DB_PATH, session_id, user_id)
        if data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="找不到此對話，或該對話不屬於當前用戶",
            )
        return SessionHistoryResponse(**data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[History] 取得 Session 歷史失敗: {e}")
        raise HTTPException(status_code=500, detail=f"取得對話歷史失敗: {str(e)}")


@router.post("/messages", summary="儲存對話訊息")
async def save_message(request: Request, body: SaveMessageRequest):
    """儲存一筆對話訊息，自動更新 Session 統計與自動標題"""
    user_id = _require_user_id(request)
    try:
        ok = svc_save_message(
            db_path=cfg.DB_PATH,
            user_id=user_id,
            session_id=body.session_id,
            role=body.role,
            content=body.content,
            model_used=body.model_used,
            tokens_used=body.tokens_used,
        )
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session 不存在或不屬於當前用戶",
            )
        return {"success": True, "message": "訊息已儲存"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[History] 儲存訊息失敗: {e}")
        raise HTTPException(status_code=500, detail=f"儲存訊息失敗: {str(e)}")


@router.delete("/sessions/{session_id}", summary="刪除指定 Session 及其對話記錄")
async def delete_session(session_id: str, request: Request):
    """刪除指定 Session 及其所有對話記錄（僅限自己名下的 Session）"""
    user_id = _require_user_id(request)
    try:
        ok = svc_delete_session(cfg.DB_PATH, session_id, user_id)
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="找不到此對話，或該對話不屬於當前用戶",
            )
        return {"success": True, "message": "對話已刪除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[History] 刪除 Session 失敗: {e}")
        raise HTTPException(status_code=500, detail=f"刪除對話失敗: {str(e)}")


@router.patch("/sessions/{session_id}/title", summary="更新 Session 標題")
async def update_session_title(session_id: str, request: Request, title: str):
    """更新對話 Session 的標題（僅限自己名下的 Session）"""
    user_id = _require_user_id(request)
    try:
        ok = svc_update_title(cfg.DB_PATH, session_id, user_id, title)
        if not ok:
            raise HTTPException(status_code=404, detail="Session 不存在或不屬於當前用戶")
        return {"success": True, "message": "標題已更新"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[History] 更新標題失敗: {e}")
        raise HTTPException(status_code=500, detail=f"更新標題失敗: {str(e)}")
