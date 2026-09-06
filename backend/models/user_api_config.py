# backend/models/user_api_config.py
"""UserApiConfig 模型 —— user_api_configs 表（BYOK：用户自带的第三方 API 配置）。

【字段】
- id          SERIAL    PRIMARY KEY
- user_id     UUID      所属用户
- service     VARCHAR   llm / vision / whisper / tts / image
- api_key     VARCHAR   用户自己的 API Key
- base_url    VARCHAR   可选，自定义 Base URL
- model       VARCHAR   可选，模型名
- is_active   BOOLEAN   DEFAULT TRUE
- updated_at  TIMESTAMP DEFAULT NOW()（onupdate 自动刷新）
- UNIQUE(user_id, service)

【说明】
- 平台不内置任何第三方 Key，全部由用户配置（BYOK）
- Key 在接口中只返回脱敏值（mask），不暴露明文
- at-rest 加密为安全加固项（见 PENDING.md）
"""
from sqlalchemy import Boolean, Column, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as UUID_PG

from config.database import Base


class UserApiConfig(Base):
    __tablename__ = "user_api_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID_PG(as_uuid=True), nullable=False, index=True)
    service = Column(String(20), nullable=False)  # llm / vision / whisper / tts / image
    api_key = Column(String(255), nullable=True)
    base_url = Column(String(255), nullable=True)
    model = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "service", name="uq_user_api_service"),
    )
