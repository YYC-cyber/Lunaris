"""
敏感词模型 —— 数据库驱动的敏感词库

支持：
- 按类别分类（curse/spam/violence/political/etc）
- 生效时间和过期时间控制
- 灵活启用/禁用
"""

from datetime import datetime
import uuid
from sqlalchemy import String, Text, DateTime, Integer, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from config.database import Base


class SensitiveWord(Base):
    """
    敏感词库

    支持动态管理敏感词，可按类别分类，支持时间范围控制
    """
    __tablename__ = "sensitive_words"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # 敏感词内容（唯一约束）
    word: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        comment="敏感词内容"
    )

    # 分类
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=True,
        comment="敏感词分类：curse/spam/violence/political/adult/scam/other"
    )

    # 启用状态
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="是否启用"
    )

    # 生效时间范围
    effective_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=True,
        comment="生效时间（NULL 表示立即生效）"
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=True,
        comment="过期时间（NULL 表示永久）"
    )

    # 创建者
    created_by: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="创建者用户 ID"
    )

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default='now()',
        nullable=False,
        comment="创建时间"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default='now()',
        nullable=False,
        comment="更新时间"
    )

    def __repr__(self):
        return f"<SensitiveWord(id={self.id}, word={self.word}, category={self.category}, is_active={self.is_active})>"
