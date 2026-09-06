"""表情包数据访问层"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.sticker import Sticker


class StickerDAO:
    """表情包数据访问对象"""

    @staticmethod
    async def get(db: AsyncSession, sticker_id: int) -> Sticker | None:
        """按 ID 获取表情包"""
        stmt = select(Sticker).where(Sticker.id == sticker_id)
        return (await db.execute(stmt)).scalar_one_or_none()

    @staticmethod
    async def get_by_emotion(db: AsyncSession, emotion: str) -> Sticker | None:
        """按情绪获取一个表情包（随机）"""
        stmt = select(Sticker).where(
            Sticker.emotion == emotion,
            Sticker.is_active == True
        ).order_by("RANDOM()")
        return (await db.execute(stmt)).scalar_one_or_none()

    @staticmethod
    async def list_all(db: AsyncSession) -> list[Sticker]:
        """获取所有启用的表情包"""
        stmt = select(Sticker).where(Sticker.is_active == True).order_by(Sticker.sort_order)
        return list((await db.execute(stmt)).scalars().all())
