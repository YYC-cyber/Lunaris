"""
用户举报模型 - 中国网络安全法和信息安全保护条例要求

用户可以举报以下违规内容：
- 骚扰、辱骂、人身攻击
- 垃圾消息、广告
- 暴力、恐怖、毒品相关内容
- 非法信息
- 其他不当内容
"""

from datetime import datetime
import uuid
from sqlalchemy import String, Text, DateTime, Integer, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from config.database import Base


class Report(Base):
    """
    用户举报记录

    中国网络安全法要求：
    - 记录违规内容和举报信息
    - 提供管理员审核和处理机制
    """
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # 举报人信息
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        comment="举报人用户 ID"
    )

    # 被举报的内容
    target_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="被举报对象类型：message/moment/profile/comment"
    )

    target_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="被举报对象 ID"
    )

    # 举报原因
    reason: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="举报原因：harassment/spam/violence/illegal/adult/scam/other"
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        comment="举报详情描述"
    )

    # 审核状态
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        comment="状态：pending/reviewing/approved/rejected/resolved"
    )

    # 审核人员
    reviewed_by: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        comment="审核人员 ID"
    )

    review_comment: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        comment="审核备注"
    )

    # 处理结果
    action_taken: Mapped[str] = mapped_column(
        String(50),
        nullable=True,
        comment="处理方式：content_deleted/user_warned/user_suspended/none"
    )

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default='now()',
        nullable=True,
        comment="举报时间"
    )

    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=True,
        comment="审核时间"
    )

    resolved_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=True,
        comment="解决时间"
    )

    def __repr__(self):
        return f"<Report(id={self.id}, reporter_id={self.reporter_id}, target_type={self.target_type}, status={self.status})>"
