"""群组公告数据访问层"""
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from models.group_announcement import GroupAnnouncement


class GroupAnnouncementDAO:
    """群组公告 DAO"""

    @staticmethod
    async def create(
        db: AsyncSession,
        group_id: int,
        content: str,
        created_by: uuid.UUID,
    ) -> GroupAnnouncement:
        """创建公告"""
        announcement = GroupAnnouncement(
            group_id=group_id,
            content=content,
            created_by=created_by,
        )
        db.add(announcement)
        await db.flush()
        return announcement

    @staticmethod
    async def get(db: AsyncSession, announcement_id: int) -> Optional[GroupAnnouncement]:
        """获取公告"""
        stmt = select(GroupAnnouncement).where(GroupAnnouncement.id == announcement_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def delete(db: AsyncSession, announcement_id: int) -> None:
        """删除公告"""
        announcement = await GroupAnnouncementDAO.get(db, announcement_id)
        if announcement:
            await db.delete(announcement)
            await db.flush()

    @staticmethod
    async def list_by_group(
        db: AsyncSession,
        group_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[List[GroupAnnouncement], int]:
        """获取群组公告列表（分页，置顶优先）"""
        stmt = select(GroupAnnouncement).where(
            GroupAnnouncement.group_id == group_id,
        ).order_by(
            desc(GroupAnnouncement.is_pinned),
            desc(GroupAnnouncement.created_at),
        )

        # 获取总数
        count_stmt = select(GroupAnnouncement).where(
            GroupAnnouncement.group_id == group_id,
        )
        count_result = await db.execute(count_stmt)
        total = len(count_result.scalars().all())

        # 获取分页数据
        result = await db.execute(stmt.offset(skip).limit(limit))
        announcements = result.scalars().all()

        return announcements, total

    @staticmethod
    async def get_pinned(db: AsyncSession, group_id: int) -> Optional[GroupAnnouncement]:
        """获取群组第一条置顶公告"""
        stmt = select(GroupAnnouncement).where(
            GroupAnnouncement.group_id == group_id,
            GroupAnnouncement.is_pinned == True,
        ).order_by(
            desc(GroupAnnouncement.created_at),
        ).limit(1)

        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def toggle_pin(
        db: AsyncSession,
        announcement_id: int,
        is_pinned: bool,
    ) -> Optional[GroupAnnouncement]:
        """切换公告的置顶状态"""
        announcement = await GroupAnnouncementDAO.get(db, announcement_id)
        if announcement:
            announcement.is_pinned = is_pinned
            announcement.updated_at = datetime.now()
            await db.flush()
        return announcement
