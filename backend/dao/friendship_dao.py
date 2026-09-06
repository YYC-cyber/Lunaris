# backend/dao/friendship_dao.py
"""FriendshipDAO —— 用户↔AI 角色 好友关系数据访问。"""
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dao.base import BaseDAO
from models.friendship import Friendship


class FriendshipDAO(BaseDAO[Friendship]):
    model = Friendship

    @classmethod
    async def get_by_user_soul(
        cls, db: AsyncSession, user_id: uuid.UUID, soul_id: int
    ) -> Optional[Friendship]:
        return (
            await db.execute(
                select(Friendship).where(
                    Friendship.user_id == user_id, Friendship.soul_id == soul_id
                )
            )
        ).scalar_one_or_none()

    @classmethod
    async def list_by_user(cls, db: AsyncSession, user_id: uuid.UUID) -> list:
        return list(
            (
                await db.execute(
                    select(Friendship).where(Friendship.user_id == user_id)
                )
            ).scalars().all()
        )

    @classmethod
    async def clear_primary(cls, db: AsyncSession, user_id: uuid.UUID) -> None:
        """清空该用户所有默认伴侣标记。"""
        from sqlalchemy import update
        await db.execute(
            update(Friendship)
            .where(Friendship.user_id == user_id)
            .values(is_primary=False)
        )

    @classmethod
    async def delete_by_user(cls, db: AsyncSession, user_id: uuid.UUID) -> int:
        """删除用户的所有好友关系（用于账户硬删除）"""
        from sqlalchemy import delete
        result = await db.execute(
            delete(Friendship).where(Friendship.user_id == user_id)
        )
        return result.rowcount or 0
