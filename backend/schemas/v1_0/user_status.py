# backend/schemas/user_status.py
"""用户在线状态 DTO。"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
import uuid


class UserStatusResponse(BaseModel):
    """用户状态信息。"""
    user_id: uuid.UUID
    username: str
    nickname: Optional[str]
    avatar_url: Optional[str]
    is_online: bool  # 根据 last_seen_at 推断（如果存在则在线）
    last_seen_at: Optional[datetime]


class OnlineUserInfo(BaseModel):
    """在线用户信息。"""
    user_id: str
    username: str
    nickname: str
    avatar_url: Optional[str]
    last_seen_at: Optional[datetime]


class OnlineUsersResponse(BaseModel):
    """在线用户列表响应。"""
    data: List[OnlineUserInfo]
    count: int
