"""
Moment 模型 —— moments 表（朋友圈动态）

【字段】
- id              SERIAL      PRIMARY KEY
- soul_id         INT         FK → souls        # 发布角色（AI 动态）
- user_id         UUID        FK → users        # 发布用户（用户动态）
- content         TEXT        NOT NULL
- images          JSONB                     # ['url1','url2']
- voice_url       TEXT                    # 10 秒语音条（P2）
- topic_tags      JSONB                   # ['#治愈','#夕阳']
- visibility      VARCHAR     DEFAULT 'public' # public/friends/private
- is_ai_generated BOOLEAN     DEFAULT TRUE
- like_count      INT         DEFAULT 0
- created_at      TIMESTAMP   DEFAULT NOW()

【索引】
- idx_moments_created (created_at DESC)
- idx_moments_soul_created (soul_id, created_at)
- idx_moments_user_id_created (user_id, created_at)
- idx_moments_visibility (visibility)

【约束】
- ck_moments_author_xor: 仅 soul_id 或 user_id 之一非 NULL
- ck_moments_visibility: visibility IN ('public', 'friends', 'private')

【说明】
- 评论单独一张表 → models/comment.py
- 点赞计数直接维护 like_count 字段
- 隐私规则：
  * public: 所有人可见
  * friends: 仅作者和好友可见
  * private: 仅作者可见
"""
# backend/models/moment.py
import uuid
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, func, Index, text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID as UUID_PG
from sqlalchemy.orm import relationship
from config.database import Base

class Moment(Base):
    __tablename__ = "moments"

    id = Column(Integer, primary_key=True, index=True)
    soul_id = Column(Integer, ForeignKey("souls.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(UUID_PG(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    content = Column(Text, nullable=False)
    images = Column(JSONB, nullable=True, default=list, server_default=text("'[]'::jsonb"))
    topic_tags = Column(JSONB, nullable=True, default=list, server_default=text("'[]'::jsonb"))
    voice_url = Column(Text, nullable=True)
    visibility = Column(String(20), nullable=False, default='public', server_default='public')
    is_ai_generated = Column(Boolean, default=True, server_default=text("true"))
    like_count = Column(Integer, default=0, server_default=text("0"))
    visible_groups = Column(JSONB, nullable=True, default=list, server_default=text("'[]'::jsonb"))  # P2-04: 分组可见列表
    hidden_user_ids = Column(JSONB, nullable=True, default=list, server_default=text("'[]'::jsonb"))  # P2-04: 隐藏用户列表
    is_deleted = Column(Boolean, default=False, server_default=text("false"))  # DB-03: 软删除标记
    deleted_at = Column(DateTime, nullable=True)  # DB-03: 软删除时间
    created_at = Column(DateTime, server_default=func.now())

    # Relationships (optional, for ORM convenience)
    soul = relationship("Soul", foreign_keys=[soul_id])
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index('idx_moments_created', 'created_at'),
        Index('idx_moments_soul_created', 'soul_id', 'created_at'),
        Index('idx_moments_user_id_created', 'user_id', 'created_at'),
        Index('idx_moments_visibility', 'visibility'),
    )