"""CrisisEventDAO —— 危机事件数据访问"""
import uuid
from typing import List, Optional
from datetime import datetime

from sqlalchemy import select, desc, join
from sqlalchemy.ext.asyncio import AsyncSession

from dao.base import BaseDAO
from models.crisis_event import CrisisEvent
from models.user import User


class CrisisEventDAO(BaseDAO[CrisisEvent]):
    model = CrisisEvent

    @classmethod
    async def list_escalated(
        cls, db: AsyncSession, limit: int = 50, offset: int = 0
    ) -> List[CrisisEvent]:
        """获取已升级的危机事件（不包括 'none' 状态）"""
        stmt = (
            select(CrisisEvent)
            .where(CrisisEvent.escalation_status != "none")
            .order_by(desc(CrisisEvent.escalated_at))
            .limit(limit)
            .offset(offset)
        )
        return list((await db.execute(stmt)).scalars().all())

    @classmethod
    async def escalate(
        cls,
        db: AsyncSession,
        event_id: int,
        assigned_to: Optional[uuid.UUID] = None,
    ) -> Optional[CrisisEvent]:
        """升级危机事件"""
        event = await cls.get(db, event_id)
        if not event:
            return None

        event.escalation_status = "escalated"
        event.assigned_to = assigned_to
        event.escalated_at = datetime.utcnow()
        await db.commit()
        return event

    @classmethod
    async def resolve(
        cls,
        db: AsyncSession,
        event_id: int,
        notes: str,
    ) -> Optional[CrisisEvent]:
        """解决危机事件"""
        event = await cls.get(db, event_id)
        if not event:
            return None

        event.escalation_status = "resolved"
        event.resolved_at = datetime.utcnow()
        event.resolution_notes = notes
        await db.commit()
        return event
