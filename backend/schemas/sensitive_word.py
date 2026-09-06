"""
敏感词相关的数据传输对象（DTO）
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


class SensitiveWordCreateRequest(BaseModel):
    """添加敏感词请求"""
    word: str = Field(..., min_length=1, max_length=100, description="敏感词")
    category: Optional[str] = Field(None, max_length=50, description="分类")
    effective_at: Optional[datetime] = Field(None, description="生效时间")
    expires_at: Optional[datetime] = Field(None, description="过期时间")


class SensitiveWordUpdateRequest(BaseModel):
    """更新敏感词请求"""
    is_active: Optional[bool] = Field(None, description="是否启用")
    category: Optional[str] = Field(None, max_length=50, description="分类")
    expires_at: Optional[datetime] = Field(None, description="过期时间")


class SensitiveWordOut(BaseModel):
    """敏感词响应"""
    id: int
    word: str
    category: Optional[str]
    is_active: bool
    effective_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SensitiveWordListOut(BaseModel):
    """敏感词列表响应"""
    total: int
    words: list[SensitiveWordOut]


class SensitiveWordStatsOut(BaseModel):
    """敏感词统计响应"""
    active_count: int
    inactive_count: int
    total_count: int
    by_category: dict[str, int]
