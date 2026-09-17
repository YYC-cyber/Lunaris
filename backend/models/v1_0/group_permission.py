"""群组权限模型"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from config.database import Base


class GroupPermission(Base):
    """群组角色权限配置"""
    __tablename__ = "group_permissions"

    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("group_chats.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), nullable=False)
    can_invite = Column(Boolean, nullable=False, default=True)
    can_kick = Column(Boolean, nullable=False, default=False)
    can_edit_info = Column(Boolean, nullable=False, default=False)
    can_delete_messages = Column(Boolean, nullable=False, default=False)
    can_pin = Column(Boolean, nullable=False, default=False)
    can_manage_roles = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, server_default="now()")
