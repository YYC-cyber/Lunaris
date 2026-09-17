# backend/dao/soul_dao.py
"""SoulDAO —— AI 角色数据访问。"""
import uuid
from typing import List

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from dao.base import BaseDAO
from models.v1_0.friendship import Friendship
from models.v1_0.soul import Soul


class SoulDAO(BaseDAO[Soul]):
    model = Soul

    @classmethod
    async def list_available(cls, db: AsyncSession, user_id: uuid.UUID, target_gender: str) -> List[Soul]:
        """可添加的异性角色（排除已配对），默认优先 + 排序。"""
        paired = select(Friendship.soul_id).where(Friendship.user_id == user_id).subquery()
        stmt = (
            select(Soul)
            .where(and_(Soul.gender == target_gender, Soul.id.notin_(paired)))
            .order_by(Soul.is_default.desc(), Soul.sort_order.asc())
        )
        return list((await db.execute(stmt)).scalars().all())

    @classmethod
    async def get_match(cls, db: AsyncSession, target_gender: str):
        """配对：目标性别的默认优先 + 排序取第一个。"""
        stmt = (
            select(Soul)
            .where(Soul.gender == target_gender)
            .order_by(Soul.is_default.desc(), Soul.sort_order.asc())
            .limit(1)
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    @classmethod
    async def list_paired(cls, db: AsyncSession, user_id: uuid.UUID) -> List[Soul]:
        """已配对角色列表。"""
        stmt = (
            select(Soul)
            .join(Friendship, Friendship.soul_id == Soul.id)
            .where(Friendship.user_id == user_id)
            .order_by(Friendship.is_primary.desc(), Soul.id.asc())
        )
        return list((await db.execute(stmt)).scalars().all())
