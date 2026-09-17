# backend/dao/memory_dao.py
"""MemoryDAO —— 长期记忆数据访问。"""
import uuid
from typing import List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from dao.base import BaseDAO
from models.v1_0.memory import MemoryRecord


class MemoryDAO(BaseDAO[MemoryRecord]):
    model = MemoryRecord

    @classmethod
    async def list_by_user_soul(
        cls, db: AsyncSession, user_id: uuid.UUID, soul_id: int, limit: int = 10
    ) -> List[MemoryRecord]:
        stmt = (
            select(MemoryRecord)
            .where(MemoryRecord.user_id == user_id, MemoryRecord.soul_id == soul_id)
            .order_by(MemoryRecord.updated_at.desc())
            .limit(limit)
        )
        return list((await db.execute(stmt)).scalars().all())

    @classmethod
    async def get_by_content(
        cls, db: AsyncSession, user_id: uuid.UUID, soul_id: int, content: str
    ) -> Optional[MemoryRecord]:
        return (
            await db.execute(
                select(MemoryRecord).where(
                    MemoryRecord.user_id == user_id,
                    MemoryRecord.soul_id == soul_id,
                    MemoryRecord.content == content,
                )
            )
        ).scalar_one_or_none()

    @classmethod
    async def list_similar(
        cls, db: AsyncSession, user_id: uuid.UUID, soul_id: int, query_vec: list, limit: int = 10
    ) -> List[MemoryRecord]:
        """按余弦相似度检索最相关的记忆（长记忆升级：语义检索）。"""
        stmt = (
            select(MemoryRecord)
            .where(
                MemoryRecord.user_id == user_id,
                MemoryRecord.soul_id == soul_id,
                MemoryRecord.embedding.is_not(None),
            )
            .order_by(MemoryRecord.embedding.cosine_distance(query_vec))
            .limit(limit)
        )
        return list((await db.execute(stmt)).scalars().all())

    @classmethod
    async def delete_by_user_soul(cls, db: AsyncSession, user_id: uuid.UUID, soul_id: int) -> int:
        """删除某用户与某角色的全部记忆（滚动摘要时替换用），返回删除条数。"""
        result = await db.execute(
            delete(MemoryRecord).where(
                MemoryRecord.user_id == user_id, MemoryRecord.soul_id == soul_id
            )
        )
        await db.commit()
        return result.rowcount or 0

    @classmethod
    async def delete_by_content(
        cls, db: AsyncSession, user_id: uuid.UUID, soul_id: int, content: str
    ) -> int:
        """按内容删除某用户与某角色的记忆（memory_tool remove/replace 用），返回删除条数。"""
        result = await db.execute(
            delete(MemoryRecord).where(
                MemoryRecord.user_id == user_id,
                MemoryRecord.soul_id == soul_id,
                MemoryRecord.content == content,
            )
        )
        await db.commit()
        return result.rowcount or 0

    @classmethod
    async def get_by_user(cls, db: AsyncSession, user_id: uuid.UUID) -> list:
        """获取用户的所有记忆（用于数据导出）"""
        stmt = select(MemoryRecord).where(MemoryRecord.user_id == user_id)
        return list((await db.execute(stmt)).scalars().all())

    @classmethod
    async def delete_by_user(cls, db: AsyncSession, user_id: uuid.UUID) -> int:
        """删除用户的所有记忆（用于账户硬删除）"""
        result = await db.execute(
            delete(MemoryRecord).where(MemoryRecord.user_id == user_id)
        )
        return result.rowcount or 0
