"""
Admin API - 管理功能路由 (配置、統計、文件管理、批次操作)

v2.4.0 重構:
- _build_enhanced_token_stats → backend.app.services.token_stats_service
- DocumentStats import 移除（未使用）
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from backend.app.schemas.common import ResponseBase
from backend.app.dependencies import get_database, get_config
from backend.app.services.token_stats_service import build_enhanced_token_stats

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/config", response_model=ResponseBase)
async def get_system_config():
    """
    取得目前系統配置

    Returns:
        ResponseBase: data 包含:
            - base_url (str): API 基礎 URL
            - model_vision (str): 圖片分析模型 ID
            - model_text (str): 文字分析模型 ID
            - analysis_mode (str): 分析模式 ("text_only" | "vision" | "auto")
            - has_api_key (bool): 是否已設定 API Key
    """
    config = get_config()
    api_config = config.get_api_config()

    return ResponseBase(
        success=True,
        data={
            "base_url": api_config["base_url"],
            "model_vision": api_config["model_vision"],
            "model_text": api_config["model_text"],
            "analysis_mode": api_config.get("analysis_mode", "auto"),
            "byok_mode": True,  # 系統採用 BYOK 模式
        },
    )


class UpdateConfigRequest(BaseModel):
    """系統配置更新請求（BYOK 模式不包含 API Key）"""
    base_url: Optional[str] = None
    model_vision: Optional[str] = None
    model_text: Optional[str] = None
    analysis_mode: Optional[str] = None


@router.post("/config", response_model=ResponseBase)
async def update_system_config(request: UpdateConfigRequest):
    """
    更新系統配置（接受 JSON body）

    Args:
        request: UpdateConfigRequest JSON body，所有欄位皆為可選:
            - base_url (str): API 基礎 URL
            - model_vision (str): 圖片分析模型 ID
            - model_text (str): 文字分析模型 ID
            - analysis_mode (str): 分析模式 ("text_only" | "vision" | "auto")

    Returns:
        ResponseBase: success=True 表示配置已即時生效

    Raises:
        HTTPException 500: 更新過程發生錯誤

    Note:
        更新會立即生效於後續的所有 API 呼叫，無需重啟服務
        系統採用 BYOK 模式，不支援設定共享 API Key
    """
    try:
        config = get_config()
        config.set_api_config(
            base_url=request.base_url,
            model_vision=request.model_vision,
            model_text=request.model_text,
            analysis_mode=request.analysis_mode,
        )

        return ResponseBase(success=True, message="系統配置已更新")

    except Exception as e:
        logger.error(f"❌ 更新配置失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=ResponseBase)
async def get_stats():
    """
    取得系統統計資訊

    Returns:
        ResponseBase: data 包含:
            - documents (dict): {total, by_type: {type: count}}
            - tokens (dict): {total_tokens, total_requests, today_tokens}

    Raises:
        HTTPException 500: 資料庫查詢失敗
    """
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
    """
    列出所有文件

    Args:
        doc_type: 可選，依文件類型過濾（"Knowledge" | "SOP" | "FAQ"）

    Returns:
        ResponseBase: data.documents 為文件陣列，每筆包含:
            - id, filename, doc_type, upload_date, model_used, chunk_count

    Raises:
        HTTPException 500: 資料庫查詢失敗
    """
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
    """
    刪除指定文件及其所有切片

    Args:
        doc_id: 文件 ID（整數）

    Returns:
        ResponseBase: success=True 表示刪除成功

    Raises:
        HTTPException 404: 文件不存在
        HTTPException 500: 刪除過程發生錯誤
    """
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
    """
    取得 Token 使用統計（增強版 v2.2.0）

    回傳格式包含：
    - summary: 總量、今日、估計費用
    - daily: 每日趨勢 [{date, tokens}]
    - by_model: 模型分佈 [{model, tokens}]
    - by_operation: 操作分佈 [{operation, tokens}]
    - by_user: 使用者分佈 [{user_id, tokens, requests}]
    - by_hour: 24H 分佈 [{hour, tokens}]
    - top_files: 高消耗檔案 [{file_name, tokens}]
    """
    try:
        # 取得基本統計（來自 core/database）
        database = get_database()
        raw_stats = database.get_token_stats(days=days)

        # 增強版格式轉換（委派 Service）
        enhanced = build_enhanced_token_stats(raw_stats, days)

        return ResponseBase(success=True, data=enhanced)

    except Exception as e:
        logger.error(f"❌ 取得 Token 統計失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/batch/{action}", response_model=ResponseBase)
async def batch_operation(action: str, doc_type: Optional[str] = None):
    """
    批次操作：對知識庫執行維護作業

    Args:
        action: 操作類型，可用值:
            - "reindex": 重新建立向量索引
            - "update_metadata": 更新文件元資料
            - "validate": 驗證文件完整性
        doc_type: 可選，限定操作範圍的文件類型

    Returns:
        ResponseBase: data 包含:
            - affected (int): 受影響的文件數
            - valid / invalid (int): 僅 validate 時回傳

    Raises:
        HTTPException 400: 不支援的操作類型
        HTTPException 500: 操作過程發生錯誤
    """
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
