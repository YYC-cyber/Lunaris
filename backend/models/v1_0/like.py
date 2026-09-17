# backend/models/like.py
from sqlalchemy import Column, Integer, DateTime, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as UUID_PG
from config.database import Base

class Like(Base):
    __tablename__ = "likes"

    id = Column(Integer, primary_key=True, index=True)
    moment_id = Column(Integer, nullable=False, index=True)
    user_id = Column(UUID_PG(as_uuid=True), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('moment_id', 'user_id', name='uq_like'),
    )