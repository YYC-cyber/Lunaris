"""群聊模型"""
import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, func, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from config.database import Base


class GroupTypeEnum(str, Enum):
    """群聊类型"""
    AI_ONLY = "ai_only"  # 仅 AI 多人聊天
    HUMAN_ONLY = "human_only"  # 仅真人群聊
    MIXED = "mixed"  # AI + 真人混合


class MemberTypeEnum(str, Enum):
    """成员类型"""
    AI = "ai"
    HUMAN = "human"


class MemberStatusEnum(str, Enum):
    """成员状态"""
    ACTIVE = "active"
    INVITED = "invited"
    DECLINED = "declined"


class InvitationStatusEnum(str, Enum):
    """邀请状态"""
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"


class GroupRoleEnum(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class GroupChat(Base):
    """群聊"""
    __tablename__ = "group_chats"

    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    group_name = Column(String(100), nullable=True)
    group_type = Column(SQLEnum(GroupTypeEnum), nullable=False)  # ai_only / human_only / mixed
    announcement = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    auto_delete_hours = Column(Integer, nullable=True)  # 自动删除时长（小时），NULL = 不删除
    is_archived = Column(Boolean, nullable=False, default=False)
    is_deleted = Column(Boolean, nullable=False, default=False)

    # 关系
    creator = relationship("User", foreign_keys=[user_id])
    members = relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")
    messages = relationship("GroupMessage", back_populates="group", cascade="all, delete-orphan")
    invitations = relationship("GroupInvitation", back_populates="group", cascade="all, delete-orphan")


class GroupMember(Base):
    """群成员"""
    __tablename__ = "group_members"

    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("group_chats.id", ondelete="CASCADE"), nullable=False)
    member_type = Column(SQLEnum(MemberTypeEnum), nullable=False)  # ai / human
    member_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    soul_id = Column(Integer, ForeignKey("souls.id", ondelete="CASCADE"), nullable=True)
    joined_at = Column(DateTime, nullable=False, server_default=func.now())
    status = Column(SQLEnum(MemberStatusEnum), nullable=False, default=MemberStatusEnum.ACTIVE)
    role = Column(String(50), nullable=False, default="member")

    # 关系
    group = relationship("GroupChat", back_populates="members")
    user = relationship("User", foreign_keys=[member_id])
    soul = relationship("Soul", foreign_keys=[soul_id])


class GroupMessage(Base):
    """群消息"""
    __tablename__ = "group_messages"

    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("group_chats.id", ondelete="CASCADE"), nullable=False)
    sender_type = Column(SQLEnum("ai", "user", name="sender_type_enum"), nullable=False)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    soul_id = Column(Integer, ForeignKey("souls.id", ondelete="CASCADE"), nullable=True)
    content = Column(Text, nullable=False)
    voice_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)
    expires_at = Column(DateTime, nullable=True)  # 消息过期时间
    is_deleted = Column(Boolean, nullable=False, default=False)

    # 关系
    group = relationship("GroupChat", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id])
    soul = relationship("Soul", foreign_keys=[soul_id])


class GroupInvitation(Base):
    """群邀请"""
    __tablename__ = "group_invitations"

    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("group_chats.id", ondelete="CASCADE"), nullable=False)
    inviter_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    invitee_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(SQLEnum(InvitationStatusEnum), nullable=False, default=InvitationStatusEnum.PENDING)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    expires_at = Column(DateTime, nullable=False)  # 邀请链接过期时间

    # 关系
    group = relationship("GroupChat", back_populates="invitations")
    inviter = relationship("User", foreign_keys=[inviter_id])
    invitee = relationship("User", foreign_keys=[invitee_id])


class GroupMemory(Base):
    """群聊记忆"""
    __tablename__ = "group_memories"

    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("group_chats.id", ondelete="CASCADE"), nullable=False)
    soul_id = Column(Integer, ForeignKey("souls.id", ondelete="CASCADE"), nullable=False)
    memory_type = Column(String(50), nullable=False)  # 'event', 'member_info', 'group_rule', etc
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, nullable=False, default=False)

    # 关系
    group = relationship("GroupChat", foreign_keys=[group_id])
    soul = relationship("Soul", foreign_keys=[soul_id])
