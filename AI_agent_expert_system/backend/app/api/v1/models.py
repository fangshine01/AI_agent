"""
Models API - 模型清單路由 (v2.2.0)

提供可用模型列表供前端 Model 選擇器使用
企業 API Proxy 同時支援 OpenAI 與 Gemini 模型
"""

import logging
from fastapi import APIRouter

import backend.config as cfg

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/list", summary="取得可用模型清單")
async def list_available_models():
    """
    回傳系統支援的所有模型清單

    企業 API 透過同一 proxy 端點支援 OpenAI 與 Gemini 模型，
    前端根據此清單渲染下拉選單。

    Returns:
        dict: {
            models: [{display_name, model_id, category, cost_label}],
            default_model: str
        }
    """
    models = []
    for model_info in cfg.AVAILABLE_MODELS:
        models.append({
            "display_name": model_info.get("display_name", ""),
            "model_id": model_info.get("model_id", ""),
            "category": model_info.get("category", "Other"),
            "cost_label": model_info.get("cost_label", "💰"),
        })

    return {
        "models": models,
        "default_model": cfg.DEFAULT_CHAT_MODEL,
    }
