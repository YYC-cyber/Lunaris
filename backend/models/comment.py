"""
Comment 模型 —— comments 表（朋友圈评论）

【字段】
- id          SERIAL      PRIMARY KEY
- moment_id   INT         FK → moments, NOT NULL
- user_id     UUID        FK → users             # 用户评论时
- soul_id     INT         FK → souls             # AI 评论时记录角色
- sender_type VARCHAR(10) CHECK IN ('user','ai')
- content     TEXT        NOT NULL
- created_at  TIMESTAMP   DEFAULT NOW()

【索引】
- idx_comments_moment (moment_id)

【说明】
- MOM-06：用户评论后，AI 以楼中楼形式在评论区公开回复
- AI 主动评论（若产品化）用 sender_type='ai'
"""

# backend/models/comment.py
"""
Comment 模型 —— comments 表（朋友圈评论）

【字段】
- id                SERIAL       PRIMARY KEY
- moment_id         INT          NOT NULL   FK → moments.id
- user_id           UUID                    FK → users.id  评论人（NULL = AI 回复）
- soul_id           INT                    FK → souls.id  AI 回复时指向角色
- parent_comment_id INT                    父评论 ID（NULL=顶级评论，支持楼中楼）
- content           TEXT         NOT NULL
- created_at        TIMESTAMP    DEFAULT NOW()

【索引】
- (moment_id, created_at) 用于按动态查评论列表
"""

from sqlalchemy import Column, Integer, Text, DateTime, Boolean, func, Index, text
from sqlalchemy.dialects.postgresql import UUID as UUID_PG
from config.database import Base


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    moment_id = Column(Integer, nullable=False, index=True)
    user_id = Column(UUID_PG(as_uuid=True), nullable=True, index=True)      # NULL = AI 回复
    soul_id = Column(Integer, nullable=True, index=True)                   # AI 回复时指向角色
    parent_comment_id = Column(Integer, nullable=True, index=True)         # 楼中楼（回复某条评论）
    content = Column(Text, nullable=False)
    is_deleted = Column(Boolean, default=False, server_default=text("false"))  # DB-03: 软删除标记
    deleted_at = Column(DateTime, nullable=True)  # DB-03: 软删除时间
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index('idx_comments_moment_created', 'moment_id', 'created_at'),
    )