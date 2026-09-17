# backend/models/memory.py
"""
MemoryRecord 模型 —— memory_records 表（长期记忆）

【字段】
- id          SERIAL       PRIMARY KEY
- user_id     UUID         FK → users.id
- soul_id     INT          FK → souls.id
- memory_type VARCHAR(20)  'user_profile' / 'long_term' / 'emotional_state'
- content     TEXT         NOT NULL   记忆内容
- created_at  TIMESTAMP    DEFAULT NOW()
- updated_at  TIMESTAMP    DEFAULT NOW()（onupdate 自动刷新）

【说明】
- v1.2：记忆写入前必须过 security.scan_memory_content（防注入/防外泄）
- 危机内容不写入本表（SAFE-05 记忆隔离）
- >50 条触发异步摘要压缩（core/memory.py，尚未实现）
"""
from sqlalchemy import Column, DateTime, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as UUID_PG
from pgvector.sqlalchemy import Vector

from config.database import Base
from clients.embedding_client import EMBEDDING_DIM


class MemoryRecord(Base):
    __tablename__ = "memory_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID_PG(as_uuid=True), nullable=False, index=True)
    soul_id = Column(Integer, nullable=False, index=True)
    memory_type = Column(String(20), nullable=False)      # user_profile/long_term/emotional_state
    content = Column(Text, nullable=False)
    embedding = Column(Vector(EMBEDDING_DIM), nullable=True)  # 语义检索（长记忆升级）
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 复合索引：快速查某用户与某角色的记忆
    __table_args__ = (
        Index('idx_memory_user_soul', 'user_id', 'soul_id'),
    )
