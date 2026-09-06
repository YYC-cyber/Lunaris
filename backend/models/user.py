"""
User 模型 —— users 表（用户）

【字段】
- id            UUID           PRIMARY KEY
- username      VARCHAR(50)    UNIQUE, NOT NULL
- password_hash VARCHAR(255)   NOT NULL          # bcrypt 哈希
- gender        VARCHAR(10)    CHECK IN ('male','female')
- nickname      VARCHAR(50)                       # 显示昵称
- avatar_url    TEXT
- birthday      DATE                             # 年龄验证
- is_active     BOOLEAN        DEFAULT TRUE
- created_at    TIMESTAMP      DEFAULT NOW()
- last_login_at TIMESTAMP

【关系】
- friendships 1:N   → Friendship
- messages    1:N   → Message
- memory_records 1:N → MemoryRecord
- crisis_events 1:N → CrisisEvent
- 默认伴侣：通过 friendships.is_primary 标记
"""

# backend/models/user.py
from sqlalchemy import Column, String, DateTime, Boolean, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from config.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    lunaris_id = Column(String(32), unique=True, nullable=True, index=True)  # 微信式主页 ID，注册时生成
    is_admin = Column(Boolean, default=False)          # 后台管理员
    api_granted_until = Column(DateTime, nullable=True)  # 平台 API 授权到期时间（NULL=未开通；付费/开通后=到期时间）
    password_hash = Column(String(255), nullable=False)
    gender = Column(String(10), nullable=False)  # 'male' 或 'female'
    nickname = Column(String(50), nullable=True)
    avatar_url = Column(String(255), nullable=True)
    bio = Column(String(200), nullable=True)
    birthday = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    role = Column(String(50), default='user', nullable=False)  # admin, manager, user
    suspended_until = Column(DateTime, nullable=True)  # 账户暂停有效期（NULL=未暂停）
    created_at = Column(DateTime, server_default=func.now())
    last_login_at = Column(DateTime, onupdate=func.now())
    last_seen_at = Column(DateTime, nullable=True)  # P2-05: 最后活跃时间（在线状态）
    theme = Column(String(20), default='light', nullable=False)  # P2-05: 主题设置（light/dark）
    font_size = Column(String(20), default='normal', nullable=False)  # P2-05: 字体大小设置

    # 关系（后续扩展，先留空）
    # messages = relationship("Message", back_populates="user")
    # memories = relationship("MemoryRecord", back_populates="user")
