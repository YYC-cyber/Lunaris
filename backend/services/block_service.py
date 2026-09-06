"""用户屏蔽服务"""
import uuid
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from config.logging_config import get_logger
from dao.user_block_dao import UserBlockDAO

logger = get_logger("block_service")


class BlockService:
    @staticmethod
    async def block(
        db: AsyncSession, blocker_id: uuid.UUID, blocked_id: uuid.UUID
    ) -> None:
        """屏蔽用户"""
        if blocker_id == blocked_id:
            logger.warning("屏蔽失败：不能屏蔽自己", extra={"user_id": str(blocker_id)})
            raise ValueError("不能屏蔽自己")
        await UserBlockDAO.block(db, blocker_id, blocked_id)
        logger.info("用户已屏蔽", extra={"blocker_id": str(blocker_id), "blocked_id": str(blocked_id)})

    @staticmethod
    async def unblock(
        db: AsyncSession, blocker_id: uuid.UUID, blocked_id: uuid.UUID
    ) -> None:
        """取消屏蔽"""
        success = await UserBlockDAO.unblock(db, blocker_id, blocked_id)
        if not success:
            logger.info("取消屏蔽失败：未屏蔽此用户", extra={"blocker_id": str(blocker_id), "blocked_id": str(blocked_id)})
            raise ValueError("未屏蔽此用户")
        logger.info("已取消屏蔽", extra={"blocker_id": str(blocker_id), "blocked_id": str(blocked_id)})

    @staticmethod
    async def is_blocked(
        db: AsyncSession, blocker_id: uuid.UUID, blocked_id: uuid.UUID
    ) -> bool:
        """检查是否已屏蔽"""
        return await UserBlockDAO.is_blocked(db, blocker_id, blocked_id)

    @staticmethod
    async def list_blocked(
        db: AsyncSession,
        blocker_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[dict]:
        """获取屏蔽用户列表"""
        return await UserBlockDAO.list_blocked(db, blocker_id, limit, offset)

    @staticmethod
    async def are_blocked(
        db: AsyncSession,
        user1_id: uuid.UUID,
        user2_id: uuid.UUID,
    ) -> bool:
        """检查两个用户是否互相屏蔽"""
        return await UserBlockDAO.are_blocked(db, user1_id, user2_id)
