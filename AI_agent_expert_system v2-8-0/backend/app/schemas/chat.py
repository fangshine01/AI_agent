"""
Chat 相關 Pydantic 模型
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """問答請求"""
    query: str = Field(..., description="使用者問題")
    query_type: str = Field(default="general", description="查詢類型: general/troubleshooting/procedure/knowledge/training")
    chat_model: str = Field(default="gpt-4o-mini", description="問答模型")
    search_limit: int = Field(default=5, ge=1, le=20, description="搜尋結果數量")
    selected_types: List[str] = Field(default=[], description="限定搜尋的文件類型")
    filters: Dict[str, Any] = Field(default={}, description="額外過濾條件")
    enable_fuzzy: bool = Field(default=True, description="啟用模糊搜尋")
    api_key: Optional[str] = Field(default=None, description="使用者 API Key")
    base_url: Optional[str] = Field(default=None, description="API Base URL")


class ChatResponse(BaseModel):
    """問答回應"""
    success: bool = True
    response: str = ""
    search_results: List[Dict[str, Any]] = []
    search_meta: Dict[str, Any] = {}
    usage: Dict[str, int] = {}
    is_direct_retrieval: bool = False
    doc_type: Optional[str] = None


class ChatHistoryItem(BaseModel):
    """聊天歷史項目"""
    role: str
    content: str
    tokens: int = 0
    timestamp: Optional[str] = None
