# backend/models/user_friendship.py
"""UserFriendship 模型 —— user_friendships 表（真人用户之间的好友申请/关系）。

【字段】
- id            SERIAL    PRIMARY KEY
- requester_id  UUID      发起申请的用户
- addressee_id  UUID      被添加的用户
- status        VARCHAR   pending(待处理) / accepted(已是好友) / rejected(已拒绝)
- created_at    TIMESTAMP DEFAULT NOW()
- accepted_at   TIMESTAMP 成为好友的时间

【说明】
- 好友关系是双向的：A→B accepted 即视为互为好友（查询时查两侧）
- 同一对用户只保留一条有效记录（查询时做双向去重）
"""
from sqlalchemy import Column, DateTime, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID as UUID_PG

from config.database import Base


class UserFriendship(Base):
    __tablename__ = "user_friendships"

    id = Column(Integer, primary_key=True, index=True)
    requester_id = Column(UUID_PG(as_uuid=True), nullable=False, index=True)
    addressee_id = Column(UUID_PG(as_uuid=True), nullable=False, index=True)
    status = Column(String(10), nullable=False, default="pending")  # pending/accepted/rejected
    created_at = Column(DateTime, server_default=func.now())
    accepted_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_user_friends_pair", "requester_id", "addressee_id"),
    )
