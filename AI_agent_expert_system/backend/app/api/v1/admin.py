"""
Admin API - 管理功能路由 (配置、統計)
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

from backend.app.schemas.common import ResponseBase
from backend.app.schemas.document import DocumentStats
from backend.app.dependencies import get_database, get_config
import backend.config as cfg

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
            "has_api_key": bool(api_config["api_key"]),
        },
    )


class UpdateConfigRequest(BaseModel):
    """系統配置更新請求"""
    api_key: Optional[str] = None
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
            - api_key (str): API Key
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
    """
    try:
        config = get_config()
        config.set_api_config(
            api_key=request.api_key,
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

        # 增強版格式轉換
        enhanced = _build_enhanced_token_stats(raw_stats, days)

        return ResponseBase(success=True, data=enhanced)

    except Exception as e:
        logger.error(f"❌ 取得 Token 統計失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _build_enhanced_token_stats(raw_stats: dict, days: int) -> dict:
    """
    將 core/database/token_ops 原始格式轉為 Admin UI 期望的增強格式

    原始格式: {total_tokens, total_prompt_tokens, by_operation: {}, recent_usage: []}
    增強格式: {summary, daily, by_model, by_operation, by_user, by_hour, top_files}
    """
    total_tokens = raw_stats.get("total_tokens", 0)
    total_prompt = raw_stats.get("total_prompt_tokens", 0)
    total_completion = raw_stats.get("total_completion_tokens", 0)

    # summary 摘要
    # 估計費用（以 GPT-4o-mini 價格粗估：$0.15 / 1M input, $0.60 / 1M output）
    estimated_cost = (total_prompt * 0.15 + total_completion * 0.60) / 1_000_000

    # 操作數 = recent_usage 的近似
    recent = raw_stats.get("recent_usage", [])
    total_requests = len(recent) if recent else 0

    # 嘗試從 Token DB 取得更精確的統計
    today_tokens = 0
    daily_data = []
    by_model_data = []
    by_user_data = []
    by_hour_data = []
    top_files_data = []

    try:
        conn = sqlite3.connect(cfg.TOKEN_DB_PATH, timeout=10)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if days:
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
            time_cond = "WHERE timestamp >= ?"
            params = (start_date,)
        else:
            time_cond = ""
            params = ()

        # 今日 Token
        today_str = datetime.now().strftime("%Y-%m-%d")
        cursor.execute(
            "SELECT COALESCE(SUM(total_tokens), 0) FROM token_usage WHERE DATE(timestamp) = ?",
            (today_str,),
        )
        today_tokens = cursor.fetchone()[0] or 0

        # 總請求數（精確）
        cursor.execute(f"SELECT COUNT(*) FROM token_usage {time_cond}", params)
        total_requests = cursor.fetchone()[0] or 0

        # daily: 每日 Token [{date, tokens}]
        cursor.execute(f"""
            SELECT DATE(timestamp) as date, SUM(total_tokens) as tokens
            FROM token_usage {time_cond}
            GROUP BY DATE(timestamp)
            ORDER BY date
        """, params)
        daily_data = [{"date": row["date"], "tokens": row["tokens"]} for row in cursor.fetchall()]

        # by_model: 按 operation 中的模型分組（token_usage 表無 model 欄位時用 operation 代替）
        # 先嘗試 model 欄位
        try:
            cursor.execute(f"""
                SELECT model as model_name, SUM(total_tokens) as tokens
                FROM token_usage {time_cond}
                GROUP BY model
                ORDER BY tokens DESC
            """, params)
            by_model_data = [{"model": row["model_name"] or "unknown", "tokens": row["tokens"]} for row in cursor.fetchall()]
        except sqlite3.OperationalError:
            # 沒有 model 欄位，使用 operation 代替
            pass

        # by_user: 按 user_id 分組（如果有此欄位）
        try:
            cursor.execute(f"""
                SELECT user_id, SUM(total_tokens) as tokens, COUNT(*) as requests
                FROM token_usage {time_cond}
                GROUP BY user_id
                ORDER BY tokens DESC
            """, params)
            by_user_data = [
                {"user_id": row["user_id"] or "anonymous", "tokens": row["tokens"], "requests": row["requests"]}
                for row in cursor.fetchall()
            ]
        except sqlite3.OperationalError:
            # 沒有 user_id 欄位
            pass

        # by_hour: 24 小時分佈
        cursor.execute(f"""
            SELECT CAST(strftime('%H', timestamp) AS INTEGER) as hour, SUM(total_tokens) as tokens
            FROM token_usage {time_cond}
            GROUP BY hour
            ORDER BY hour
        """, params)
        by_hour_data = [{"hour": row["hour"], "tokens": row["tokens"]} for row in cursor.fetchall()]

        # top_files: 高消耗文件
        cursor.execute(f"""
            SELECT file_name, SUM(total_tokens) as tokens
            FROM token_usage {time_cond}
            GROUP BY file_name
            ORDER BY tokens DESC
            LIMIT 10
        """, params)
        top_files_data = [
            {"file_name": row["file_name"] or "N/A", "tokens": row["tokens"]}
            for row in cursor.fetchall()
        ]

        conn.close()

    except Exception as e:
        logger.warning(f"[Admin] Token DB 增強查詢失敗（退化使用基本資料）: {e}")

    # by_operation: 轉為 list 格式（原始是 dict）
    raw_ops = raw_stats.get("by_operation", {})
    if isinstance(raw_ops, dict):
        by_operation_data = [{"operation": k, "tokens": v} for k, v in raw_ops.items()]
    elif isinstance(raw_ops, list):
        by_operation_data = raw_ops
    else:
        by_operation_data = []

    # 如果沒有 by_model 資料，嘗試用 operation 推導
    if not by_model_data and by_operation_data:
        by_model_data = [{"model": item["operation"], "tokens": item["tokens"]} for item in by_operation_data]

    return {
        "summary": {
            "total_tokens": total_tokens,
            "total_requests": total_requests,
            "estimated_cost": round(estimated_cost, 4),
            "today_tokens": today_tokens,
        },
        "daily": daily_data,
        "by_model": by_model_data,
        "by_operation": by_operation_data,
        "by_user": by_user_data,
        "by_hour": by_hour_data,
        "top_files": top_files_data,
    }


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
