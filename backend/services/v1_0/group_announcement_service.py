"""群组公告服务"""
import uuid
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from dao.v1_0.group_announcement_dao import GroupAnnouncementDAO
from models.v1_0.group_announcement import GroupAnnouncement


class GroupAnnouncementService:
    """群组公告服务"""

    @staticmethod
    async def create(
        db: AsyncSession,
        group_id: int,
        content: str,
        created_by: uuid.UUID,
    ) -> GroupAnnouncement:
        """创建公告"""
        return await GroupAnnouncementDAO.create(db, group_id, content, created_by)

    @staticmethod
    async def delete(db: AsyncSession, announcement_id: int) -> None:
        """删除公告"""
        return await GroupAnnouncementDAO.delete(db, announcement_id)

    @staticmethod
    async def list_by_group(
        db: AsyncSession,
        group_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[List[GroupAnnouncement], int]:
        """获取群组公告列表"""
        return await GroupAnnouncementDAO.list_by_group(db, group_id, skip, limit)

    @staticmethod
    async def get_pinned(db: AsyncSession, group_id: int) -> Optional[GroupAnnouncement]:
        """获取群组置顶公告"""
        return await GroupAnnouncementDAO.get_pinned(db, group_id)

    @staticmethod
    async def toggle_pin(
        db: AsyncSession,
        announcement_id: int,
        is_pinned: bool,
    ) -> Optional[GroupAnnouncement]:
        """切换公告置顶状态"""
        return await GroupAnnouncementDAO.toggle_pin(db, announcement_id, is_pinned)
