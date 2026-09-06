# backend/dao/user_friendship_dao.py
"""UserFriendshipDAO —— 真人好友关系数据访问（FRI）。"""
import uuid
from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from dao.base import BaseDAO
from models.user_friendship import UserFriendship


class UserFriendshipDAO(BaseDAO[UserFriendship]):
    model = UserFriendship

    @classmethod
    async def get_pair(
        cls, db: AsyncSession, requester_id: uuid.UUID, addressee_id: uuid.UUID
    ) -> Optional[UserFriendship]:
        return (
            await db.execute(
                select(UserFriendship).where(
                    UserFriendship.requester_id == requester_id,
                    UserFriendship.addressee_id == addressee_id,
                )
            )
        ).scalar_one_or_none()

    @classmethod
    async def get_accepted_between(
        cls, db: AsyncSession, a: uuid.UUID, b: uuid.UUID
    ) -> Optional[UserFriendship]:
        """双向 accepted 关系查询。"""
        return (
            await db.execute(
                select(UserFriendship).where(
                    UserFriendship.status == "accepted",
                    or_(
                        (UserFriendship.requester_id == a) & (UserFriendship.addressee_id == b),
                        (UserFriendship.requester_id == b) & (UserFriendship.addressee_id == a),
                    ),
                )
            )
        ).scalar_one_or_none()

    @classmethod
    async def list_friend_ids(cls, db: AsyncSession, user_id: uuid.UUID) -> List[uuid.UUID]:
        """我的好友 ID 列表（双向 accepted）。"""
        rels = (
            await db.execute(
                select(UserFriendship).where(
                    UserFriendship.status == "accepted",
                    or_(
                        UserFriendship.requester_id == user_id,
                        UserFriendship.addressee_id == user_id,
                    ),
                )
            )
        ).scalars().all()
        return [
            r.requester_id if r.addressee_id == user_id else r.addressee_id for r in rels
        ]

    @classmethod
    async def list_pending(cls, db: AsyncSession, user_id: uuid.UUID) -> list:
        """我收到待处理的申请。"""
        stmt = (
            select(UserFriendship)
            .where(
                UserFriendship.addressee_id == user_id,
                UserFriendship.status == "pending",
            )
            .order_by(UserFriendship.created_at.desc())
        )
        return list((await db.execute(stmt)).scalars().all())
