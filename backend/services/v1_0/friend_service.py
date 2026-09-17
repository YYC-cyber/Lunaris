# backend/services/friend_service.py
"""好友服务 —— 真人用户之间按 lunaris_id 添加好友（数据访问走 DAO 层）。"""
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from config.logging_config import get_logger
from dao.user_dao import UserDAO
from dao.v1_0.user_friendship_dao import UserFriendshipDAO
from models.user import User
from models.v1_0.user_friendship import UserFriendship

logger = get_logger("friend_service")


class FriendService:
    @staticmethod
    async def search_by_lunaris_id(
        db: AsyncSession, user_id: uuid.UUID, lunaris_id: str
    ) -> Optional[User]:
        """按 lunaris_id 搜索用户（排除自己）。"""
        user = await UserDAO.get_by_lunaris_id(db, lunaris_id)
        if user and user.id == user_id:
            return None  # 不能加自己
        return user

    @staticmethod
    async def _are_friends(db: AsyncSession, a: uuid.UUID, b: uuid.UUID) -> bool:
        return (await UserFriendshipDAO.get_accepted_between(db, a, b)) is not None

    @staticmethod
    async def send_request(
        db: AsyncSession, requester_id: uuid.UUID, addressee_id: uuid.UUID
    ) -> UserFriendship:
        """发送好友申请；若对方已申请过你，直接互相通过。"""
        if requester_id == addressee_id:
            logger.warning("好友申请失败：不能添加自己", extra={"requester_id": str(requester_id)})
            raise ValueError("不能添加自己")
        if await FriendService._are_friends(db, requester_id, addressee_id):
            logger.info("好友申请失败：已是好友", extra={"requester_id": str(requester_id), "addressee_id": str(addressee_id)})
            raise ValueError("你们已经是好友")

        from services.block_service import BlockService
        if await BlockService.are_blocked(db, requester_id, addressee_id):
            raise ValueError("无法添加已屏蔽的用户")

        # 对方先加过你（反向 pending）→ 直接通过
        reverse = await UserFriendshipDAO.get_pair(db, addressee_id, requester_id)
        if reverse and reverse.status == "pending":
            return await UserFriendshipDAO.update(
                db, reverse,
                status="accepted",
                accepted_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )

        # 已有正向记录
        existing = await UserFriendshipDAO.get_pair(db, requester_id, addressee_id)
        if existing:
            if existing.status == "pending":
                raise ValueError("已发送过申请，等待对方处理")
            # rejected → 允许重发
            return await UserFriendshipDAO.update(
                db, existing, status="pending", accepted_at=None
            )

        return await UserFriendshipDAO.create(
            db, requester_id=requester_id, addressee_id=addressee_id, status="pending"
        )

    @staticmethod
    async def handle_request(
        db: AsyncSession, user_id: uuid.UUID, friend_id: uuid.UUID, action: str
    ) -> None:
        """处理收到的申请：accept / reject。"""
        rel = await UserFriendshipDAO.get_pair(db, friend_id, user_id)
        if not rel or rel.status != "pending":
            raise ValueError("没有待处理的申请")
        if action == "accept":
            await UserFriendshipDAO.update(
                db, rel,
                status="accepted",
                accepted_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            logger.info("好友申请已接受", extra={"user_id": str(user_id), "friend_id": str(friend_id)})
        elif action == "reject":
            await UserFriendshipDAO.update(db, rel, status="rejected")
            logger.info("好友申请已拒绝", extra={"user_id": str(user_id), "friend_id": str(friend_id)})
        else:
            raise ValueError("action 只能是 accept / reject")

    @staticmethod
    async def list_friends(db: AsyncSession, user_id: uuid.UUID) -> List[User]:
        """我的好友列表（双向 accepted）。"""
        friend_ids = await UserFriendshipDAO.list_friend_ids(db, user_id)
        return await UserDAO.get_many(db, friend_ids)

    @staticmethod
    async def list_pending_requests(
        db: AsyncSession, user_id: uuid.UUID
    ) -> List[Dict]:
        """我收到待处理的好友申请。"""
        rels = await UserFriendshipDAO.list_pending(db, user_id)
        result = []
        for r in rels:
            requester = await UserDAO.get(db, r.requester_id)
            if requester:
                result.append({
                    "user_id": str(requester.id),
                    "lunaris_id": requester.lunaris_id,
                    "nickname": requester.nickname or requester.username,
                    "avatar_url": requester.avatar_url,
                })
        return result

    @staticmethod
    async def remove_friend(db: AsyncSession, user_id: uuid.UUID, friend_id: uuid.UUID) -> None:
        """删除好友。"""
        rel = await UserFriendshipDAO.get_accepted_between(db, user_id, friend_id)
        if not rel:
            raise ValueError("你们不是好友")
        await UserFriendshipDAO.delete(db, rel)

    @staticmethod
    async def search_users(
        db: AsyncSession,
        keyword: str,
        gender: Optional[str] = None,
        active_after: Optional[datetime] = None,
        sort_by: str = "activity",
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[User], int]:
        """搜索用户（支持性别、活跃度筛选和排序）。

        Args:
            keyword: 搜索关键词（匹配 nickname/username/bio）
            gender: 性别筛选（'male'/'female'，可选）
            active_after: 最后活跃时间下限（可选）
            sort_by: 排序方式（'name'/'activity'/'added'）
            limit: 分页限制
            offset: 分页偏移

        Returns:
            (users, total_count)
        """
        filters = [
            or_(
                User.nickname.ilike(f"%{keyword}%"),
                User.username.ilike(f"%{keyword}%"),
                User.bio.ilike(f"%{keyword}%"),
            )
        ]

        if gender:
            filters.append(User.gender == gender)

        if active_after:
            filters.append(User.last_seen_at >= active_after)

        # 基础查询
        stmt = select(User).where(and_(*filters))

        # 排序
        if sort_by == "name":
            stmt = stmt.order_by(User.nickname.asc(), User.username.asc())
        elif sort_by == "added":
            stmt = stmt.order_by(User.created_at.desc())
        else:  # activity（默认）
            stmt = stmt.order_by(User.last_seen_at.desc().nulls_last())

        # 查询总数
        count_stmt = select(func.count()).select_from(User).where(and_(*filters))
        total = (await db.execute(count_stmt)).scalar_one()

        # 分页查询
        results = list(
            (await db.execute(stmt.offset(offset).limit(limit))).scalars().all()
        )

        return results, total
