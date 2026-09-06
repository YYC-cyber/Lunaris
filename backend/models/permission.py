# backend/models/permission.py
from sqlalchemy import Column, String, Boolean, DateTime, func
from config.database import Base

class Permission(Base):
    __tablename__ = "permissions"

    id = Column(String(36), primary_key=True)
    name = Column(String(100), unique=True, nullable=False, index=True)  # admin, manager, user
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description
        }

class Role(Base):
    __tablename__ = "roles"

    id = Column(String(36), primary_key=True)
    name = Column(String(100), unique=True, nullable=False, index=True)  # admin, manager, user
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description
        }
