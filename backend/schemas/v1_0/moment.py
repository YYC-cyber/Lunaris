# backend/schemas/moment.py
"""朋友圈 DTO（Data Transfer Objects）"""
import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

# ============ 请求 DTO ============

class MomentPublishIn(BaseModel):
    """发布朋友圈请求"""
    content: str = Field(..., min_length=1, max_length=2000)
    images: List[str] = Field(default_factory=list, max_items=9)
    topic_tags: Optional[List[str]] = Field(default=None, max_items=5)
    visibility: str = Field(default="public", pattern="^(public|friends|private)$")
    visible_groups: List[str] = Field(default_factory=list, max_items=10)  # P2-04: 分组可见列表（如 ["close_friends", "family"]）
    hidden_user_ids: List[uuid.UUID] = Field(default_factory=list, max_items=100)  # P2-04: 隐藏用户列表


class MomentVisibilityIn(BaseModel):
    """更新隐私设置请求"""
    visibility: str = Field(..., pattern="^(public|friends|private)$")
    visible_groups: List[str] = Field(default_factory=list, max_items=10)  # P2-04
    hidden_user_ids: List[uuid.UUID] = Field(default_factory=list, max_items=100)  # P2-04


class CommentIn(BaseModel):
    """评论请求"""
    content: str = Field(..., min_length=1, max_length=500)
    parent_comment_id: Optional[int] = None


# ============ 响应 DTO ============

class CommentOut(BaseModel):
    """评论响应"""
    id: int
    user_id: Optional[uuid.UUID]
    soul_id: Optional[int]
    soul_name: Optional[str] = None
    content: str
    parent_comment_id: Optional[int]
    created_at: Optional[datetime]
    is_ai: bool

    class Config:
        from_attributes = True


class MomentOut(BaseModel):
    """单个动态响应"""
    id: int
    soul_id: Optional[int]
    soul_name: Optional[str] = None
    user_id: Optional[uuid.UUID] = None
    author_name: Optional[str] = None
    content: str
    images: List[str]
    topic_tags: List[str]
    voice_url: Optional[str] = None
    visibility: str
    is_ai_generated: bool
    like_count: int
    is_liked: bool = False
    is_mine: bool = False
    visible_groups: List[str] = []  # P2-04
    hidden_user_ids: List[uuid.UUID] = []  # P2-04
    created_at: Optional[datetime]
    comments: List[CommentOut] = []

    class Config:
        from_attributes = True


class MomentListOut(BaseModel):
    """动态列表响应（分页）"""
    data: List[MomentOut]
    total: int
    limit: int
    offset: int
