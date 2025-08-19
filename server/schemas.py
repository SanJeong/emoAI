"""공통 스키마 정의"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class MessageType(str, Enum):
    """메시지 타입"""
    OPEN_SESSION = "open_session"
    USER_MESSAGE = "user_message"
    FINAL_TEXT = "final_text"
    META = "meta"
    EOT = "eot"
    ERROR = "error"


class ClientStyle(BaseModel):
    """클라이언트 스타일 설정"""
    formality: str = "반말"  # 반말/존댓말
    
    
class UserMessage(BaseModel):
    """사용자 메시지"""
    type: MessageType = MessageType.USER_MESSAGE
    session_id: str
    message_id: str
    text: str
    client_style: Optional[ClientStyle] = None
    

class OpenSession(BaseModel):
    """세션 열기"""
    type: MessageType = MessageType.OPEN_SESSION
    session_id: str
    

class AgentResponse(BaseModel):
    """에이전트 응답"""
    type: MessageType
    message_id: Optional[str] = None
    text: Optional[str] = None
    used_ops: Optional[List[str]] = None
    error: Optional[str] = None
    

class PlannerOutput(BaseModel):
    """플래너 출력"""
    plan_id: str
    ops: List[Dict[str, Any]]
    draft: str
    risk_flags: Dict[str, bool] = Field(default_factory=lambda: {
        "overspeed": False,
        "boundary_touch": False
    })
    

class MemoryContext(BaseModel):
    """메모리 컨텍스트"""
    today_context: Optional[str] = None
    highlights: List[str] = Field(default_factory=list)
    pinned_facts: Dict[str, Any] = Field(default_factory=dict)
    recent_episodes: List[Dict[str, Any]] = Field(default_factory=list)
    schema_summary: Optional[str] = None
