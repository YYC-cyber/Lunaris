"""群组禁言服务"""
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from dao.group_mute_dao import GroupMuteDAO
from models.group_mute import GroupMute


class GroupMuteService:
    """群组禁言服务"""

    @staticmethod
    async def mute(
        db: AsyncSession,
        group_id: int,
        user_id: uuid.UUID,
        duration_minutes: int,
        muted_by: uuid.UUID,
    ) -> GroupMute:
        """禁言用户"""
        muted_until = datetime.now() + timedelta(minutes=duration_minutes)
        return await GroupMuteDAO.mute(db, group_id, user_id, muted_until, muted_by)

    @staticmethod
    async def unmute(db: AsyncSession, group_id: int, user_id: uuid.UUID) -> None:
        """解除用户禁言"""
        return await GroupMuteDAO.unmute(db, group_id, user_id)

    @staticmethod
    async def get_active_mute(
        db: AsyncSession,
        group_id: int,
        user_id: uuid.UUID,
    ) -> Optional[GroupMute]:
        """获取用户当前的禁言记录"""
        return await GroupMuteDAO.get_active_mute(db, group_id, user_id)

    @staticmethod
    async def list_muted_users(
        db: AsyncSession,
        group_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[List[Dict], int]:
        """获取群组被禁言用户列表"""
        return await GroupMuteDAO.list_muted_users(db, group_id, skip, limit)
