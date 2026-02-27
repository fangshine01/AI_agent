"""
文件相關 Pydantic 模型
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class DocumentUpload(BaseModel):
    """文件上傳請求"""
    doc_type: str = Field(..., description="文件類型: Knowledge/Training/Procedure/Troubleshooting")
    analysis_mode: str = Field(default="auto", description="分析模式: text_only/vision/auto")
    text_model: Optional[str] = Field(default=None, description="文字分析模型")
    vision_model: Optional[str] = Field(default=None, description="視覺分析模型")


class DocumentInfo(BaseModel):
    """文件資訊"""
    id: int
    filename: str
    doc_type: str
    upload_date: Optional[str] = None
    analysis_mode: Optional[str] = None
    model_used: Optional[str] = None
    file_size: Optional[int] = None
    category: Optional[str] = None
    tags: Optional[str] = None
    processing_time: Optional[float] = None
    summary: Optional[str] = None
    status: str = "active"


class DocumentStats(BaseModel):
    """文件統計"""
    total_documents: int = 0
    by_type: Dict[str, int] = {}


class ProcessingStatus(BaseModel):
    """處理狀態"""
    filename: str
    status: str  # 'pending', 'processing', 'completed', 'failed'
    message: Optional[str] = None
    doc_id: Optional[int] = None


class SearchRequest(BaseModel):
    """搜尋請求"""
    query: str = Field(..., description="搜尋查詢")
    top_k: int = Field(default=5, ge=1, le=50, description="回傳結果數量")
    doc_type: Optional[str] = Field(default=None, description="限定文件類型")
    filters: Dict[str, Any] = Field(default={}, description="額外過濾條件")
    enable_fuzzy: bool = Field(default=True, description="啟用模糊搜尋")
    api_key: Optional[str] = None
    base_url: Optional[str] = None


class SearchResult(BaseModel):
    """搜尋結果"""
    success: bool = True
    intent: str = ""
    strategy: str = ""
    results: List[Dict[str, Any]] = []
    meta: Dict[str, Any] = {}
