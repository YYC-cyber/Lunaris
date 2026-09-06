"""
Friendship 模型 —— friendships 表（用户↔角色 好友关系）

【字段】
- id             SERIAL       PRIMARY KEY
- user_id        UUID         FK → users
- soul_id        INT          FK → souls
- nickname       VARCHAR(50)              # 用户备注名
- intimacy_level INT          DEFAULT 0   # 亲密度 0-100
- is_primary     BOOLEAN      DEFAULT FALSE  # 是否默认伴侣
- last_chat_at   TIMESTAMP
- created_at     TIMESTAMP    DEFAULT NOW()
- UNIQUE(user_id, soul_id)

【说明】
- is_primary 同时只有一个为 True（按 user_id 分组唯一），
  切换伴侣时由 soul_service 处理互斥
- 亲密度驱动 context_service 的对话状态（角色语气随亲密度变化）
"""

# backend/models/friendship.py
from sqlalchemy import Column, Integer, UUID, String, DateTime, func, UniqueConstraint, Boolean
from sqlalchemy.dialects.postgresql import UUID as UUID_PG
from sqlalchemy.orm import relationship
from config.database import Base

class Friendship(Base):
    __tablename__ = "friendships"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID_PG(as_uuid=True), nullable=False, index=True)   # FK → users.id
    soul_id = Column(Integer, nullable=False, index=True)                 # FK → souls.id
    nickname = Column(String(50), nullable=True)                          # 用户给 AI 起的昵称
    intimacy_level = Column(Integer, default=0)                           # 亲密度 0-100
    is_primary = Column(Boolean, default=False)                           # 是否为默认伴侣
    last_chat_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # 复合唯一约束：一个用户不能重复添加同一个 AI
    __table_args__ = (
        UniqueConstraint('user_id', 'soul_id', name='uq_user_soul'),
    )

    # 关系（后续扩展）
    # user = relationship("User", back_populates="friendships")
    # soul = relationship("Soul", back_populates="friendships")