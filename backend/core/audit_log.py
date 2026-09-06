# backend/core/audit_log.py
"""审计日志（三层内容安全的第三层 + 危机/违规事件）。

- log_audit：追加一条审计记录（不阻塞主流程，失败仅打日志）
"""
import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models.audit_log import AuditLog


async def log_audit(
    db: AsyncSession,
    user_id: Optional[uuid.UUID],
    event_type: str,
    content: dict = None,
    risk_level: str = "normal",
) -> None:
    """追加审计记录。由调用方统一 commit（或本函数独立 commit）。"""
    try:
        db.add(AuditLog(
            user_id=user_id,
            request_id=uuid.uuid4(),
            event_type=event_type,
            content=content or {},
            risk_level=risk_level,
        ))
    except Exception as e:
        print(f"⚠️ 审计日志写入失败: {e}")
