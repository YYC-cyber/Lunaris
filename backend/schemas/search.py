# backend/schemas/search.py
"""搜索结果 DTO —— 消息搜索。"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
import uuid


class MessageSearchResult(BaseModel):
    """单条消息搜索结果。"""
    message_id: int
    content: str
    sender_id: uuid.UUID
    sender_name: str  # nickname 或 username
    created_at: datetime
    conversation_id: Optional[int] = None
    group_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_message(cls, msg, sender_user=None):
        """从 Message 对象构建（需要包含 sender_user 信息）。"""
        if sender_user:
            sender_name = sender_user.nickname or sender_user.username
        else:
            sender_name = "Unknown"
        return cls(
            message_id=msg.id,
            content=msg.content,
            sender_id=msg.user_id,
            sender_name=sender_name,
            created_at=msg.created_at,
            conversation_id=msg.conversation_id,
            group_id=None,  # 如果需要支持群聊消息，可从 msg 对象中获取
        )


class SearchMessagesRequest(BaseModel):
    """搜索消息请求体（POST 版本）。"""
    keyword: str
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    user_id: Optional[str] = None
    limit: int = 50
    offset: int = 0


class SearchMessagesResponse(BaseModel):
    """搜索消息响应。"""
    data: List[MessageSearchResult]
    total: int  # 总数
    limit: int
    offset: int
