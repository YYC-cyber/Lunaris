"""用户屏蔽 DAO —— 数据访问"""
import uuid
from typing import List, Optional
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from dao.base import BaseDAO
from models.user_block import UserBlock
from models.user import User


class UserBlockDAO(BaseDAO[UserBlock]):
    model = UserBlock

    @classmethod
    async def block(
        cls, db: AsyncSession, blocker_id: uuid.UUID, blocked_id: uuid.UUID
    ) -> UserBlock:
        """屏蔽用户（重复屏蔽返回现有记录）"""
        existing = await cls.get_pair(db, blocker_id, blocked_id)
        if existing:
            return existing
        return await cls.create(db, blocker_id=blocker_id, blocked_id=blocked_id)

    @classmethod
    async def unblock(
        cls, db: AsyncSession, blocker_id: uuid.UUID, blocked_id: uuid.UUID
    ) -> bool:
        """取消屏蔽"""
        block_record = await cls.get_pair(db, blocker_id, blocked_id)
        if not block_record:
            return False
        await cls.delete(db, block_record)
        return True

    @classmethod
    async def is_blocked(
        cls, db: AsyncSession, blocker_id: uuid.UUID, blocked_id: uuid.UUID
    ) -> bool:
        """检查是否已屏蔽"""
        return (await cls.get_pair(db, blocker_id, blocked_id)) is not None

    @classmethod
    async def get_pair(
        cls, db: AsyncSession, blocker_id: uuid.UUID, blocked_id: uuid.UUID
    ) -> Optional[UserBlock]:
        """获取特定屏蔽关系"""
        stmt = select(UserBlock).where(
            UserBlock.blocker_id == blocker_id,
            UserBlock.blocked_id == blocked_id,
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    @classmethod
    async def list_blocked(
        cls,
        db: AsyncSession,
        blocker_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[dict]:
        """获取用户屏蔽的用户列表（分页，包含用户信息）"""
        stmt = (
            select(UserBlock, User)
            .join(User, UserBlock.blocked_id == User.id)
            .where(UserBlock.blocker_id == blocker_id)
            .order_by(desc(UserBlock.created_at))
            .limit(limit)
            .offset(offset)
        )
        rows = list((await db.execute(stmt)).all())
        return [
            {
                "user_id": str(user.id),
                "username": user.username,
                "nickname": user.nickname or user.username,
                "avatar_url": user.avatar_url,
                "blocked_at": block.created_at,
            }
            for block, user in rows
        ]

    @classmethod
    async def are_blocked(
        cls,
        db: AsyncSession,
        user1_id: uuid.UUID,
        user2_id: uuid.UUID,
    ) -> bool:
        """检查两个用户是否互相屏蔽（任意一方屏蔽都返回 True）"""
        stmt = select(UserBlock).where(
            or_(
                and_(UserBlock.blocker_id == user1_id, UserBlock.blocked_id == user2_id),
                and_(UserBlock.blocker_id == user2_id, UserBlock.blocked_id == user1_id),
            )
        )
        return (await db.execute(stmt)).scalar_one_or_none() is not None
