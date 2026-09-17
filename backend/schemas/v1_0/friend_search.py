# backend/schemas/friend_search.py
"""用户搜索结果 DTO。"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
import uuid


class UserSearchResult(BaseModel):
    """用户搜索结果。"""
    user_id: uuid.UUID
    username: str
    nickname: Optional[str]
    avatar_url: Optional[str]
    bio: Optional[str]
    gender: str
    last_seen_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_user(cls, user):
        """从 User 对象构建。"""
        return cls(
            user_id=user.id,
            username=user.username,
            nickname=user.nickname,
            avatar_url=user.avatar_url,
            bio=user.bio,
            gender=user.gender,
            last_seen_at=user.last_seen_at,
        )


class UserSearchResponse(BaseModel):
    """用户搜索响应。"""
    data: List[UserSearchResult]
    total: int  # 总数
    limit: int
    offset: int
