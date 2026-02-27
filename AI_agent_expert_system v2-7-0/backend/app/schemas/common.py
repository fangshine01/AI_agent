"""
通用 Pydantic 資料模型
"""

from typing import Any, Optional
from pydantic import BaseModel


class ResponseBase(BaseModel):
    """統一回應格式"""
    success: bool = True
    message: str = ""
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """錯誤回應格式"""
    success: bool = False
    message: str
    error_code: Optional[str] = None
    detail: Optional[str] = None


class PaginationParams(BaseModel):
    """分頁參數"""
    page: int = 1
    page_size: int = 20
    sort_by: Optional[str] = None
    sort_order: str = "desc"
