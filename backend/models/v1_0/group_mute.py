"""群组禁言模型"""
from datetime import datetime

from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from config.database import Base


class GroupMute(Base):
    """群组禁言记录"""
    __tablename__ = "group_mutes"

    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("group_chats.id", ondelete="CASCADE"), nullable=False, index=True)
    muted_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    muted_until = Column(DateTime, nullable=False, index=True)
    muted_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default="now()")
