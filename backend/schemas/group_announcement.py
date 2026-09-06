"""群组公告 Schema"""
from typing import List

from pydantic import BaseModel


class GroupAnnouncementCreateRequest(BaseModel):
    """创建公告请求"""
    content: str


class GroupAnnouncementOut(BaseModel):
    """公告信息"""
    id: int
    group_id: int
    content: str
    created_by: str
    is_pinned: bool
    created_at: str
    updated_at: str


class AnnouncementsListOut(BaseModel):
    """公告列表"""
    announcements: List[GroupAnnouncementOut]
    total: int
    skip: int
    limit: int
