"""
申诉相关的数据传输对象（DTO）
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


class AppealCreateRequest(BaseModel):
    """创建申诉请求"""
    target_type: str = Field(..., description="申诉对象类型")
    target_id: str = Field(..., description="申诉对象 ID")
    reason: str = Field(..., max_length=2000, description="申诉原因详情")
    report_id: Optional[int] = Field(None, description="关联的举报 ID（可选）")


class AppealReviewRequest(BaseModel):
    """审核申诉请求"""
    approved: bool = Field(..., description="是否批准申诉")
    comment: str = Field(..., max_length=500, description="审核意见")


class AppealOut(BaseModel):
    """申诉响应"""
    id: int
    user_id: uuid.UUID
    report_id: Optional[int]
    target_type: str
    target_id: str
    reason: str
    status: str
    admin_comment: Optional[str]
    reviewed_by: Optional[uuid.UUID]
    reviewed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class AppealListOut(BaseModel):
    """申诉列表响应"""
    total: int
    appeals: list[AppealOut]


class AppealStatsOut(BaseModel):
    """申诉统计响应"""
    pending: int
    approved: int
    rejected: int
    total: int
