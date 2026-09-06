# backend/models/audit_log.py
"""AuditLog 模型 —— audit_logs 表（审计日志）。

【字段】
- id          SERIAL    PRIMARY KEY
- user_id     UUID      触发用户
- request_id  UUID      请求追踪 ID
- event_type  VARCHAR   user_question / api_call / tool_use / crisis_detected
- content     JSONB     详细数据
- risk_level  VARCHAR   normal / warning / high
- created_at  TIMESTAMP DEFAULT NOW()
"""
from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as UUID_PG

from config.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID_PG(as_uuid=True), nullable=True, index=True)
    request_id = Column(UUID_PG(as_uuid=True), nullable=True)
    event_type = Column(String(30), nullable=False)
    content = Column(JSONB, nullable=True)
    risk_level = Column(String(10), nullable=False, default="normal")
    created_at = Column(DateTime, server_default=func.now())
