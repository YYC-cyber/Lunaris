# backend/services/user_status_service.py
"""用户在线状态服务。"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dao.user_dao import UserDAO
from models.user import User
from ws.connection_manager import get_connection_manager
from schemas.v1_0.user_status import UserStatusResponse


class UserStatusService:
    # 在线超时时长：超过此时间未更新 last_seen_at 则认为离线（秒）
    ONLINE_TIMEOUT_SECONDS = 300

    @staticmethod
    async def update_user_last_seen(
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> None:
        """更新用户的 last_seen_at 为当前时间。"""
        user = await UserDAO.get(db, user_id)
        if user:
            await UserDAO.update(
                db,
                user,
                last_seen_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )

    @staticmethod
    async def get_online_users(db: AsyncSession) -> List[User]:
        """获取所有在线用户（根据 WebSocket 连接管理器）。"""
        manager = get_connection_manager()
        online_user_ids = manager.get_all_online()

        if not online_user_ids:
            return []

        # 转换为 UUID
        try:
            user_ids = [uuid.UUID(uid) for uid in online_user_ids]
        except (ValueError, TypeError):
            return []

        # 批量查询用户信息
        users = await UserDAO.get_many(db, user_ids)
        return users

    @staticmethod
    async def get_user_status(
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> Optional[UserStatusResponse]:
        """获取单个用户的在线状态。"""
        user = await UserDAO.get(db, user_id)
        if not user:
            return None

        manager = get_connection_manager()
        is_online = manager.get_online_count(str(user_id)) > 0

        return UserStatusResponse(
            user_id=user.id,
            username=user.username,
            nickname=user.nickname,
            avatar_url=user.avatar_url,
            is_online=is_online,
            last_seen_at=user.last_seen_at,
        )

    @staticmethod
    async def broadcast_user_event(
        user_id: uuid.UUID,
        is_online: bool,
    ) -> None:
        """向所有连接的客户端广播用户上线/下线事件。"""
        manager = get_connection_manager()
        event_type = "user_online" if is_online else "user_offline"

        # 获取所有在线用户，向他们广播
        online_users = manager.get_all_online()
        for online_user_id in online_users:
            await manager.push(
                user_id=online_user_id,
                event_type=event_type,
                event_id=str(user_id),
                data={
                    "user_id": str(user_id),
                    "timestamp": int(datetime.now(timezone.utc).timestamp()),
                },
            )
