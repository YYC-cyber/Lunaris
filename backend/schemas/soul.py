# backend/schemas/soul.py
"""
角色 DTO —— 用于角色列表/广场接口的响应结构

【内容】
- SoulOut: 角色信息（不含完整人格文件，只返回展示字段）
- SoulBriefOut: 列表用的精简版
"""

from typing import List, Optional

from pydantic import BaseModel


class SoulOut(BaseModel):
    """角色信息（完整展示用）"""
    id: int
    name: str                      # 英文名（aiden）
    display_name: str              # 中文显示名（艾登）
    gender: str                    # male / female
    first_greeting: str            # 开场白
    avatar_url: Optional[str]
    voice_id: Optional[str]
    tags: Optional[List[str]]      # JSONB → Python list
    is_default: bool
    sort_order: int

    class Config:
        from_attributes = True     # 允许从 ORM 对象直接转换


class SoulBriefOut(BaseModel):
    """角色精简版（列表用）"""
    id: int
    name: str
    display_name: str
    gender: str
    avatar_url: Optional[str]
    tags: Optional[List[str]]
    is_default: bool

    class Config:
        from_attributes = True
