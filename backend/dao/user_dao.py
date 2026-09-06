# backend/dao/user_dao.py
"""UserDAO —— 用户数据访问。"""
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dao.base import BaseDAO
from models.user import User


class UserDAO(BaseDAO[User]):
    model = User

    @classmethod
    async def get_by_username(cls, db: AsyncSession, username: str) -> Optional[User]:
        return (
            await db.execute(select(User).where(User.username == username))
        ).scalar_one_or_none()

    @classmethod
    async def get_by_lunaris_id(cls, db: AsyncSession, lunaris_id: str) -> Optional[User]:
        return (
            await db.execute(select(User).where(User.lunaris_id == lunaris_id))
        ).scalar_one_or_none()

    @classmethod
    async def get_many(cls, db: AsyncSession, ids) -> list:
        """按 ID 列表批量查。"""
        if not ids:
            return []
        return list(
            (await db.execute(select(User).where(User.id.in_(ids)))).scalars().all()
        )

    @classmethod
    async def search(cls, db: AsyncSession, keyword: str, limit: int = 20) -> list:
        from sqlalchemy import or_
        stmt = (
            select(User)
            .where(or_(User.username.ilike(f"%{keyword}%"), User.lunaris_id.ilike(f"%{keyword}%")))
            .limit(limit)
        )
        return list((await db.execute(stmt)).scalars().all())
