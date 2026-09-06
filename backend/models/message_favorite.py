"""MessageFavorite 模型 —— message_favorites 表（消息收藏）。

【字段】
- id          SERIAL    PRIMARY KEY
- user_id     UUID      收藏用户
- message_id  INT       被收藏的消息
- category    VARCHAR   分类（默认 '默认'）
- created_at  DATETIME  收藏时间
- UNIQUE(user_id, message_id)
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, func, Index
from sqlalchemy.dialects.postgresql import UUID as UUID_PG

from config.database import Base


class MessageFavorite(Base):
    __tablename__ = "message_favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID_PG(as_uuid=True), nullable=False, index=True)
    message_id = Column(Integer, ForeignKey('messages.id', ondelete='CASCADE'), nullable=False, index=True)
    category = Column(String(50), nullable=False, default='默认')
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('user_id', 'message_id', name='uq_message_favorites_user_message'),
        Index('idx_message_favorites_user_id', 'user_id'),
        Index('idx_message_favorites_created_at', 'created_at'),
    )
