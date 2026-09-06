"""AppealDAO —— 用户申诉数据访问"""
import uuid
from typing import List, Optional, Dict
from datetime import datetime

from sqlalchemy import select, update, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from dao.base import BaseDAO
from models.appeal import Appeal


class AppealDAO(BaseDAO[Appeal]):
    model = Appeal

    @classmethod
    async def list_by_user(
        cls, db: AsyncSession, user_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> List[Appeal]:
        """获取用户发起的所有申诉"""
        stmt = (
            select(Appeal)
            .where(Appeal.user_id == user_id)
            .order_by(desc(Appeal.created_at))
            .limit(limit)
            .offset(offset)
        )
        return list((await db.execute(stmt)).scalars().all())

    @classmethod
    async def list_pending(
        cls, db: AsyncSession, limit: int = 50, offset: int = 0
    ) -> List[Appeal]:
        """获取待审核的申诉"""
        stmt = (
            select(Appeal)
            .where(Appeal.status == "pending")
            .order_by(desc(Appeal.created_at))
            .limit(limit)
            .offset(offset)
        )
        return list((await db.execute(stmt)).scalars().all())

    @classmethod
    async def review(
        cls,
        db: AsyncSession,
        appeal_id: int,
        reviewed_by: uuid.UUID,
        approved: bool,
        admin_comment: str,
    ) -> Optional[Appeal]:
        """审核申诉"""
        appeal = await cls.get(db, appeal_id)
        if not appeal:
            return None

        appeal.status = "approved" if approved else "rejected"
        appeal.reviewed_by = reviewed_by
        appeal.admin_comment = admin_comment
        appeal.reviewed_at = datetime.utcnow()

        await db.commit()
        return appeal

    @classmethod
    async def count_by_status(cls, db: AsyncSession, status: str) -> int:
        """按状态计数"""
        stmt = select(func.count()).select_from(Appeal).where(Appeal.status == status)
        return (await db.execute(stmt)).scalar_one()

    @classmethod
    async def count_all(cls, db: AsyncSession) -> int:
        """获取总申诉数"""
        stmt = select(func.count()).select_from(Appeal)
        return (await db.execute(stmt)).scalar_one()

    @classmethod
    async def get_stats(cls, db: AsyncSession) -> Dict[str, int]:
        """获取申诉统计"""
        pending = await cls.count_by_status(db, "pending")
        approved = await cls.count_by_status(db, "approved")
        rejected = await cls.count_by_status(db, "rejected")
        return {
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
            "total": pending + approved + rejected,
        }
