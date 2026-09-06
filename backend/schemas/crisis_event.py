"""
危机事件相关的数据传输对象（DTO）
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


class CrisisEscalateRequest(BaseModel):
    """升级危机事件请求"""
    assigned_to: Optional[uuid.UUID] = Field(None, description="分配给的管理员用户 ID")


class CrisisResolveRequest(BaseModel):
    """解决危机事件请求"""
    notes: str = Field(..., max_length=1000, description="解决备注")


class CrisisEventOut(BaseModel):
    """危机事件响应"""
    id: int
    user_id: uuid.UUID
    soul_id: Optional[int]
    message_id: Optional[int]
    trigger_content: str
    risk_level: str
    hit_channel: str
    response_type: str
    escalation_status: str
    assigned_to: Optional[uuid.UUID]
    escalated_at: Optional[datetime]
    resolved_at: Optional[datetime]
    resolution_notes: Optional[str]
    handled_at: Optional[datetime]

    class Config:
        from_attributes = True


class CrisisEventListOut(BaseModel):
    """危机事件列表响应"""
    total: int
    events: list[CrisisEventOut]
