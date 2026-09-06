# backend/models/crisis_event.py
"""CrisisEvent 模型 —— crisis_events 表（危机干预事件，SAFE）。

【字段】
- id             SERIAL    PRIMARY KEY
- user_id        UUID      触发用户
- soul_id        INT       会话角色
- message_id     INT       触发消息
- trigger_content TEXT     触发原文
- risk_level     VARCHAR   warning / high / critical
- hit_channel    VARCHAR   keywords / llm / both
- response_type  VARCHAR   template_reply / escalated
- handled_at     TIMESTAMP DEFAULT NOW()
- escalation_status VARCHAR  none / escalated / in_progress / resolved
- assigned_to    UUID      分配给的管理员用户 ID
- escalated_at   TIMESTAMP 升级时间
- resolved_at    TIMESTAMP 解决时间
- resolution_notes TEXT     解决备注
"""
from sqlalchemy import Column, DateTime, Integer, String, Text, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as UUID_PG

from config.database import Base


class CrisisEvent(Base):
    __tablename__ = "crisis_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID_PG(as_uuid=True), nullable=False, index=True)
    soul_id = Column(Integer, nullable=True)
    message_id = Column(Integer, nullable=True)
    trigger_content = Column(Text, nullable=False)
    risk_level = Column(String(10), nullable=False, default="high")
    hit_channel = Column(String(30), nullable=False)
    response_type = Column(String(20), nullable=False, default="template_reply")
    handled_at = Column(DateTime, server_default=func.now())

    # 升级工作流
    escalation_status = Column(String(20), nullable=False, default="none")
    assigned_to = Column(UUID_PG(as_uuid=True), nullable=True, index=True)
    escalated_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)
