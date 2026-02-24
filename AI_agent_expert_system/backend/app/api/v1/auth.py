"""
Auth API - 安全驗證路由 (v2.3.0)

用戶登入時先驗證 API Key 有效性：
- 透過企業 API Proxy (OpenAI 相容端點) 的 List Models API (免費)
- 驗證通過後回傳 user_hash + 13 個可用模型清單
- 防止無效 Key 浪費後端資源
"""

import hashlib
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.app.middleware.identity import hash_user_identity, mask_api_key
import backend.config as cfg

logger = logging.getLogger(__name__)
router = APIRouter()


# ========== 請求/回應模型 ==========

class VerifyRequest(BaseModel):
    """API Key 驗證請求"""
    key: str = Field(..., description="用戶的 API Key")
    username: Optional[str] = Field(default=None, description="可選的用戶名稱 (共用 Key 時區分)")
    provider: str = Field(default="openai", description="API 供應商 (企業 Proxy 統一使用 openai)")
    base_url: Optional[str] = Field(default=None, description="企業 API Proxy 端點 URL")


class VerifyResponse(BaseModel):
    """API Key 驗證回應"""
    status: str = "valid"
    user_hash: str = ""
    provider: str = ""
    message: str = ""
    available_models: list = []


# ========== 驗證邏輯 ==========

async def _verify_api_key(api_key: str, base_url: Optional[str] = None) -> dict:
    """
    驗證 API Key 有效性
    透過企業 API Proxy (OpenAI 相容) 的 GET /models (完全免費) 驗證
    """
    import httpx

    url_to_check = "http://innoai.cminl.oa/agency/proxy/models"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                url_to_check,
                headers={"Authorization": f"Bearer {api_key}"}
            )

            if resp.status_code == 200:
                return {"valid": True}
            elif resp.status_code == 401:
                return {"valid": False, "error": "API Key 無效或已過期"}
            elif resp.status_code == 429:
                return {"valid": False, "error": "API Key 已達到速率限制，請稍後再試"}
            else:
                return {"valid": False, "error": f"驗證失敗 (HTTP {resp.status_code})"}

    except httpx.TimeoutException:
        return {"valid": False, "error": "驗證逾時，請檢查網路連線或 Base URL"}
    except Exception as e:
        return {"valid": False, "error": f"驗證過程出錯: {str(e)}"}


# ========== API Endpoint ==========

@router.post("/verify", response_model=VerifyResponse, summary="驗證 API Key 有效性")
async def verify_api_key(request: VerifyRequest):
    """
    驗證用戶的 API Key 是否有效

    流程:
    1. 接收前端傳來的 Key
    2. 根據 provider 呼叫對應的 List Models API（免費）
    3. 成功: 回傳 user_hash + 可用模型清單
    4. 失敗: 回傳錯誤訊息，前端禁止進入主畫面
    """
    if not request.key or len(request.key.strip()) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API Key 不可為空或長度不足"
        )

    masked_key = mask_api_key(request.key)
    logger.info(f"[Auth] 驗證 Key: {masked_key}")

    # 透過企業 API Proxy 驗證（統一 OpenAI 相容格式）
    result = await _verify_api_key(request.key, request.base_url)

    if not result["valid"]:
        logger.warning(f"[Auth] Key 驗證失敗: {masked_key} - {result['error']}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result["error"]
        )

    # 產生 user_hash
    user_hash = hash_user_identity(request.key, request.username)

    logger.info(f"[Auth] Key 驗證成功: {masked_key} -> user_hash={user_hash}")

    # 回傳系統配置的模型清單（企業 API 透過同一 proxy 支援所有模型）
    configured_models = [
        {
            "display_name": model_info.get("display_name", ""),
            "model_id": model_info.get("model_id", ""),
            "category": model_info.get("category", "Other"),
            "cost_label": model_info.get("cost_label", "💰"),
        }
        for model_info in cfg.AVAILABLE_MODELS
    ]

    return VerifyResponse(
        status="valid",
        user_hash=user_hash,
        provider=request.provider,
        message="API Key 驗證成功",
        available_models=configured_models,
    )
