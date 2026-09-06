# backend/models/system_log.py
from sqlalchemy import Column, String, DateTime, Text, func
from sqlalchemy.orm import declarative_base
from datetime import datetime
import uuid

from config.database import Base

class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), nullable=False, index=True)
    action = Column(String(100), nullable=False)  # login, create_user, update_user, delete_user, etc.
    target = Column(String(255), nullable=True)  # 操作目标（如用户名、资源ID）
    details = Column(Text, nullable=True)  # 详细信息（JSON格式）
    status = Column(String(20), default='success')  # success, fail
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'action': self.action,
            'target': self.target,
            'details': self.details,
            'status': self.status,
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
