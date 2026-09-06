"""用户屏蔽 —— user_blocks 表（用户屏蔽关系）"""
import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, Index, Integer, func
from sqlalchemy.dialects.postgresql import UUID as UUID_PG

from config.database import Base


class UserBlock(Base):
    __tablename__ = "user_blocks"

    id = Column(Integer, primary_key=True, index=True)
    blocker_id = Column(UUID_PG(as_uuid=True), nullable=False, index=True)
    blocked_id = Column(UUID_PG(as_uuid=True), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_user_blocks_blocker_id", "blocker_id"),
        Index("idx_user_blocks_blocked_id", "blocked_id"),
    )
