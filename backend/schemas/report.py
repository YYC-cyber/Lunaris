"""
举报相关的数据传输对象（DTO）
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


class ReportCreateIn(BaseModel):
    """创建举报请求"""
    target_type: str = Field(
        ...,
        pattern="^(message|moment|profile|comment|user)$",
        description="被举报对象类型"
    )
    target_id: int = Field(..., description="被举报对象 ID")
    reason: str = Field(
        ...,
        pattern="^(harassment|spam|violence|illegal|adult|scam|other)$",
        description="举报原因"
    )
    description: Optional[str] = Field(None, max_length=500, description="详细描述")


class ReportReviewIn(BaseModel):
    """审核举报请求"""
    review_comment: str = Field(..., max_length=500, description="审核意见")


class ReportActionIn(BaseModel):
    """处理举报请求"""
    action_taken: str = Field(
        ...,
        pattern="^(content_deleted|user_warned|user_suspended|none)$",
        description="采取的行动"
    )


class ReportOut(BaseModel):
    """举报响应"""
    id: int
    reporter_id: uuid.UUID
    target_type: str
    target_id: int
    reason: str
    description: Optional[str]
    status: str
    reviewed_by: Optional[uuid.UUID]
    review_comment: Optional[str]
    action_taken: Optional[str]
    created_at: Optional[datetime]
    reviewed_at: Optional[datetime]
    resolved_at: Optional[datetime]

    class Config:
        from_attributes = True


class ReportListOut(BaseModel):
    """举报列表响应"""
    total: int
    pending_count: int
    reports: list[ReportOut]
