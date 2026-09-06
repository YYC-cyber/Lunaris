"""MessageEditHistory 模型 —— message_edit_history 表（消息编辑历史记录）。

【字段】
- id          SERIAL    PRIMARY KEY
- message_id  INT       被编辑消息的 ID（FK messages.id）
- old_content TEXT      编辑前的内容
- edited_at   DATETIME  编辑时间
"""
from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, Index

from config.database import Base


class MessageEditHistory(Base):
    __tablename__ = "message_edit_history"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey('messages.id', ondelete='CASCADE'), nullable=False, index=True)
    old_content = Column(Text, nullable=False)
    edited_at = Column(DateTime, nullable=False)

    __table_args__ = (
        Index('idx_message_edit_history_message_id', 'message_id'),
    )
