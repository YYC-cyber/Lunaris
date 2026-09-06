"""群组禁言 Schema"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class GroupMuteRequest(BaseModel):
    """禁言请求"""
    duration_minutes: int


class MuteUserOut(BaseModel):
    """禁言用户信息"""
    mute_id: int
    user_id: str
    username: str
    muted_until: str
    muted_by: str
    created_at: str


class MutedUsersListOut(BaseModel):
    """禁言用户列表"""
    users: List[MuteUserOut]
    total: int
    skip: int
    limit: int
