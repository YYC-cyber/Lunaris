# backend/models/message.py
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, func, Index, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID as UUID_PG
from config.database import Base

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    # 统一消息表：真人聊天用 conversation_id（soul_id 为空）；AI 聊天用 soul_id（conversation_id 为空）
    conversation_id = Column(Integer, nullable=True, index=True)
    user_id = Column(UUID_PG(as_uuid=True), nullable=False, index=True)
    soul_id = Column(Integer, nullable=True, index=True)  # AI 消息时指向角色
    sender_type = Column(String(10), nullable=False)      # 'user' 或 'ai'
    content = Column(Text, nullable=False)
    msg_type = Column(String(10), nullable=False, default="text")  # text/sticker/image
    emotion = Column(String(20), nullable=True)
    voice_url = Column(Text, nullable=True)
    image_url = Column(Text, nullable=True)              # msg_type=image
    sticker_id = Column(Integer, nullable=True)          # msg_type=sticker
    is_recalled = Column(Boolean, default=False)
    is_edited = Column(Boolean, default=False)
    edited_at = Column(DateTime, nullable=True)
    forwarded_from_id = Column(Integer, ForeignKey('messages.id', ondelete='SET NULL'), nullable=True)
    is_deleted = Column(Boolean, default=False, server_default=text("false"))  # DB-03: 软删除标记
    deleted_at = Column(DateTime, nullable=True)  # DB-03: 软删除时间
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index('idx_user_soul_created', 'user_id', 'soul_id', 'created_at'),
        Index('idx_conversation_created', 'conversation_id', 'created_at'),
    )