# backend/models/conversation.py
"""Conversation 模型 —— conversations 表（真人好友之间的会话，FRI-06）。

【字段】
- id              SERIAL    PRIMARY KEY
- user1_id        UUID      NOT NULL   参与者1（较小 ID，应用层保证排序）
- user2_id        UUID      NOT NULL   参与者2
- last_message_id INT                 最后一条消息 ID（预览用）
- last_message_at TIMESTAMP           最后消息时间（会话列表排序）
- created_at      TIMESTAMP DEFAULT NOW()
- updated_at      TIMESTAMP DEFAULT NOW()（onupdate 自动刷新）

【约束】
- UNIQUE(user1_id, user2_id)：两人之间只有一个会话
- 应用层保证 user1_id < user2_id（按 UUID 排序）
- INDEX(updated_at DESC)：会话列表按最新消息排序
"""
from sqlalchemy import (
    Column, DateTime, Index, Integer, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import UUID as UUID_PG

from config.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user1_id = Column(UUID_PG(as_uuid=True), nullable=False, index=True)
    user2_id = Column(UUID_PG(as_uuid=True), nullable=False, index=True)
    last_message_id = Column(Integer, nullable=True)
    last_message_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("user1_id", "user2_id", name="uq_conversation_users"),
        Index("idx_conversations_updated", "updated_at"),
    )
