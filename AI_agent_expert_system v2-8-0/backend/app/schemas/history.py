"""
Chat History Pydantic 模型
從 api/v1/history.py 抽離，保持 Router 端點乾淨
"""

from typing import Optional, List
from pydantic import BaseModel, Field


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
