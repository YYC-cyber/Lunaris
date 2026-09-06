"""ReportDAO —— 用户举报数据访问"""
import uuid
from typing import List, Optional
from datetime import datetime

from sqlalchemy import select, update, desc
from sqlalchemy.ext.asyncio import AsyncSession

from dao.base import BaseDAO
from models.report import Report


class ReportDAO(BaseDAO[Report]):
    model = Report

    @classmethod
    async def list_pending(
        cls, db: AsyncSession, limit: int = 50, offset: int = 0
    ) -> List[Report]:
        """获取待审核的举报"""
        stmt = (
            select(Report)
            .where(Report.status == "pending")
            .order_by(desc(Report.created_at))
            .limit(limit)
            .offset(offset)
        )
        return list((await db.execute(stmt)).scalars().all())

    @classmethod
    async def list_by_user(
        cls, db: AsyncSession, user_id: uuid.UUID, limit: int = 20
    ) -> List[Report]:
        """获取用户发起的所有举报"""
        stmt = (
            select(Report)
            .where(Report.reporter_id == user_id)
            .order_by(desc(Report.created_at))
            .limit(limit)
        )
        return list((await db.execute(stmt)).scalars().all())

    @classmethod
    async def list_by_target(
        cls, db: AsyncSession, target_type: str, target_id: int
    ) -> List[Report]:
        """获取针对某个内容的所有举报"""
        stmt = (
            select(Report)
            .where(Report.target_type == target_type, Report.target_id == target_id)
            .order_by(desc(Report.created_at))
        )
        return list((await db.execute(stmt)).scalars().all())

    @classmethod
    async def count_pending(cls, db: AsyncSession) -> int:
        """获取待审核举报数量"""
        stmt = select(Report).where(Report.status == "pending")
        result = await db.execute(stmt)
        return len(result.scalars().all())

    @classmethod
    async def review(
        cls,
        db: AsyncSession,
        report_id: int,
        reviewed_by: uuid.UUID,
        review_comment: str,
    ) -> Optional[Report]:
        """审核举报"""
        report = await cls.get(db, report_id)
        if not report:
            return None

        report.status = "reviewing"
        report.reviewed_by = reviewed_by
        report.review_comment = review_comment
        report.reviewed_at = datetime.utcnow()

        await db.commit()
        return report

    @classmethod
    async def resolve(
        cls,
        db: AsyncSession,
        report_id: int,
        action_taken: str,
    ) -> Optional[Report]:
        """处理举报"""
        report = await cls.get(db, report_id)
        if not report:
            return None

        report.status = "resolved"
        report.action_taken = action_taken
        report.resolved_at = datetime.utcnow()

        await db.commit()
        return report
