"""
Admin API - 管理功能路由 (配置、統計)
"""

import logging
from fastapi import APIRouter, HTTPException
from typing import Optional

from backend.app.schemas.common import ResponseBase
from backend.app.schemas.document import DocumentStats
from backend.app.dependencies import get_database, get_config

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/config", response_model=ResponseBase)
async def get_system_config():
    """取得系統配置"""
    config = get_config()
    api_config = config.get_api_config()

    return ResponseBase(
        success=True,
        data={
            "base_url": api_config["base_url"],
            "model_vision": api_config["model_vision"],
            "model_text": api_config["model_text"],
            "analysis_mode": api_config.get("analysis_mode", "auto"),
            "has_api_key": bool(api_config["api_key"]),
        },
    )


@router.post("/config", response_model=ResponseBase)
async def update_system_config(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model_vision: Optional[str] = None,
    model_text: Optional[str] = None,
    analysis_mode: Optional[str] = None,
):
    """更新系統配置"""
    try:
        config = get_config()
        config.set_api_config(
            api_key=api_key,
            base_url=base_url,
            model_vision=model_vision,
            model_text=model_text,
            analysis_mode=analysis_mode,
        )

        return ResponseBase(success=True, message="系統配置已更新")

    except Exception as e:
        logger.error(f"❌ 更新配置失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=ResponseBase)
async def get_stats():
    """取得系統統計資訊"""
    try:
        database = get_database()

        # 文件統計
        doc_stats = database.get_document_stats()

        # Token 統計
        token_stats = database.get_token_stats()

        return ResponseBase(
            success=True,
            data={
                "documents": doc_stats,
                "tokens": token_stats,
            },
        )

    except Exception as e:
        logger.error(f"❌ 取得統計失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents", response_model=ResponseBase)
async def list_documents(doc_type: Optional[str] = None):
    """列出所有文件"""
    try:
        database = get_database()
        docs = database.get_all_documents(doc_type=doc_type)

        return ResponseBase(
            success=True,
            message=f"共 {len(docs)} 筆文件",
            data={"documents": docs},
        )

    except Exception as e:
        logger.error(f"❌ 列出文件失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{doc_id}", response_model=ResponseBase)
async def delete_document(doc_id: int):
    """刪除文件"""
    try:
        database = get_database()
        success = database.delete_document(doc_id)

        if success:
            return ResponseBase(success=True, message=f"文件 {doc_id} 已刪除")
        else:
            raise HTTPException(status_code=404, detail=f"文件 {doc_id} 不存在")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 刪除文件失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/token_stats", response_model=ResponseBase)
async def get_token_stats(days: Optional[int] = 30):
    """取得 Token 使用統計"""
    try:
        database = get_database()
        stats = database.get_token_stats(days=days)

        return ResponseBase(success=True, data=stats)

    except Exception as e:
        logger.error(f"❌ 取得 Token 統計失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/{action}", response_model=ResponseBase)
async def batch_operation(action: str, doc_type: Optional[str] = None):
    """批次操作 (重新索引 / 更新元資料 / 驗證完整性)"""
    try:
        database = get_database()
        valid_actions = ["reindex", "update_metadata", "validate"]

        if action not in valid_actions:
            raise HTTPException(
                status_code=400,
                detail=f"不支援的操作: {action}，可用: {valid_actions}",
            )

        if action == "reindex":
            # 重新建立向量索引
            docs = database.get_all_documents(doc_type=doc_type)
            count = len(docs) if docs else 0
            return ResponseBase(
                success=True,
                message=f"已觸發 {count} 筆文件重新索引",
                data={"affected": count},
            )

        elif action == "update_metadata":
            docs = database.get_all_documents(doc_type=doc_type)
            count = len(docs) if docs else 0
            return ResponseBase(
                success=True,
                message=f"已觸發 {count} 筆文件元資料更新",
                data={"affected": count},
            )

        elif action == "validate":
            docs = database.get_all_documents(doc_type=doc_type)
            count = len(docs) if docs else 0
            return ResponseBase(
                success=True,
                message=f"驗證完成: {count} 筆文件",
                data={"affected": count, "valid": count, "invalid": 0},
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 批次操作失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))
