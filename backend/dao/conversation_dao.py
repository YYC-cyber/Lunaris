# backend/dao/conversation_dao.py
"""ConversationDAO —— 真人会话数据访问（FRI-06）。"""
import uuid
from typing import Optional

from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from dao.base import BaseDAO
from models.conversation import Conversation


def _pair(user_a: uuid.UUID, user_b: uuid.UUID) -> tuple:
    return (user_a, user_b) if str(user_a) < str(user_b) else (user_b, user_a)


class ConversationDAO(BaseDAO[Conversation]):
    model = Conversation

    @classmethod
    async def get_by_pair(cls, db: AsyncSession, user_a: uuid.UUID, user_b: uuid.UUID) -> Optional[Conversation]:
        u1, u2 = _pair(user_a, user_b)
        return (
            await db.execute(
                select(Conversation).where(
                    Conversation.user1_id == u1, Conversation.user2_id == u2
                )
            )
        ).scalar_one_or_none()

    @classmethod
    async def list_by_user(cls, db: AsyncSession, user_id: uuid.UUID) -> list:
        """某用户的全部会话（按最后消息时间倒序）。"""
        stmt = (
            select(Conversation)
            .where(or_(Conversation.user1_id == user_id, Conversation.user2_id == user_id))
            .order_by(desc(Conversation.updated_at))
        )
        return list((await db.execute(stmt)).scalars().all())
