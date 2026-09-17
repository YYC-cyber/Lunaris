"""群组禁言 DAO —— 数据访问层"""
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from dao.base import BaseDAO
from models.v1_0.group_mute import GroupMute
from models.user import User


class GroupMuteDAO(BaseDAO[GroupMute]):
    """群组禁言 DAO"""
    model = GroupMute

    @classmethod
    async def mute(
        cls,
        db: AsyncSession,
        group_id: int,
        user_id: uuid.UUID,
        muted_until: datetime,
        muted_by: uuid.UUID,
    ) -> GroupMute:
        """添加或更新禁言记录"""
        existing = await cls.get_pair(db, group_id, user_id)
        if existing:
            return await cls.update(
                db,
                existing,
                muted_until=muted_until,
                muted_by=muted_by,
            )
        return await cls.create(
            db,
            group_id=group_id,
            muted_user_id=user_id,
            muted_until=muted_until,
            muted_by=muted_by,
        )

    @classmethod
    async def unmute(cls, db: AsyncSession, group_id: int, user_id: uuid.UUID) -> None:
        """移除禁言记录"""
        mute = await cls.get_pair(db, group_id, user_id)
        if mute:
            await cls.delete(db, mute)

    @classmethod
    async def get_pair(
        cls,
        db: AsyncSession,
        group_id: int,
        user_id: uuid.UUID,
    ) -> Optional[GroupMute]:
        """获取特定的禁言关系"""
        stmt = select(GroupMute).where(
            GroupMute.group_id == group_id,
            GroupMute.muted_user_id == user_id,
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    @classmethod
    async def get_active_mute(
        cls,
        db: AsyncSession,
        group_id: int,
        user_id: uuid.UUID,
    ) -> Optional[GroupMute]:
        """获取当前有效的禁言记录（未过期）"""
        stmt = select(GroupMute).where(
            GroupMute.group_id == group_id,
            GroupMute.muted_user_id == user_id,
            GroupMute.muted_until > datetime.now(),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def list_muted_users(
        cls,
        db: AsyncSession,
        group_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[List[dict], int]:
        """获取群组中被禁言的用户列表（仅有效禁言，分页）"""
        # 获取总数
        count_stmt = select(GroupMute).where(
            GroupMute.group_id == group_id,
            GroupMute.muted_until > datetime.now(),
        )
        count_result = await db.execute(count_stmt)
        total = len(count_result.scalars().all())

        # 获取分页数据（包含用户信息）
        stmt = (
            select(GroupMute, User)
            .join(User, GroupMute.muted_user_id == User.id)
            .where(
                GroupMute.group_id == group_id,
                GroupMute.muted_until > datetime.now(),
            )
            .order_by(desc(GroupMute.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        rows = result.fetchall()

        muted_users = [
            {
                "mute_id": mute.id,
                "user_id": str(mute.muted_user_id),
                "username": user.nickname,
                "muted_until": mute.muted_until.isoformat(),
                "muted_by": str(mute.muted_by),
                "created_at": mute.created_at.isoformat(),
            }
            for mute, user in rows
        ]

        return muted_users, total

