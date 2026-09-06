"""CommentDAO —— 评论数据访问"""
import uuid
from typing import List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from dao.base import BaseDAO
from models.comment import Comment


class CommentDAO(BaseDAO[Comment]):
    model = Comment

    @classmethod
    async def get_by_moment(cls, db: AsyncSession, moment_id: int) -> List[Comment]:
        """获取某个朋友圈动态的所有评论"""
        stmt = select(Comment).where(Comment.moment_id == moment_id)
        return list((await db.execute(stmt)).scalars().all())

    @classmethod
    async def delete_by_user(cls, db: AsyncSession, user_id: uuid.UUID) -> int:
        """删除用户的所有评论（用于账户硬删除）"""
        result = await db.execute(
            delete(Comment).where(Comment.user_id == user_id)
        )
        return result.rowcount or 0
