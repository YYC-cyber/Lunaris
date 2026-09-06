"""用户资料更新 DTO"""
from pydantic import BaseModel, Field
from typing import Optional


class UserProfileUpdateRequest(BaseModel):
    """用户资料更新请求"""
    nickname: Optional[str] = Field(None, min_length=1, max_length=50, description="昵称")
    avatar_url: Optional[str] = Field(None, max_length=500, description="头像 URL")
    bio: Optional[str] = Field(None, max_length=200, description="个人简介")

    class Config:
        from_attributes = True
