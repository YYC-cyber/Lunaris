"""
用户申诉模型 - 对系统决定（内容删除、用户禁用等）的申诉

用户可以就以下决定申诉：
- 内容被删除
- 账户被禁用
- 被举报处理
"""

from datetime import datetime
import uuid
from sqlalchemy import String, Text, DateTime, Integer, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from config.database import Base


class Appeal(Base):
    """
    用户申诉记录

    用户可对系统的处理决定（内容删除、账户禁用等）提出申诉
    """
    __tablename__ = "appeals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # 申诉人信息
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        comment="申诉人用户 ID"
    )

    # 关联的举报（可选）
    report_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("reports.id", ondelete="SET NULL"),
        nullable=True,
        comment="关联的举报 ID（可选）"
    )

    # 被申诉的内容
    target_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="申诉对象类型：message/moment/profile/comment/etc"
    )

    target_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="申诉对象 ID"
    )

    # 申诉原因
    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="申诉详情"
    )

    # 审核状态
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        comment="状态：pending/approved/rejected"
    )

    # 审核人员和意见
    admin_comment: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        comment="管理员审核意见"
    )

    reviewed_by: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        comment="审核人员 ID"
    )

    # 时间戳
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=True,
        comment="审核时间"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default='now()',
        nullable=False,
        comment="申诉时间"
    )

    def __repr__(self):
        return f"<Appeal(id={self.id}, user_id={self.user_id}, target_type={self.target_type}, status={self.status})>"
