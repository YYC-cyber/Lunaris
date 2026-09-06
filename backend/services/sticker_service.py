"""
表情包服务（STK）—— 按情绪取表情 + 收藏/管理（STK-04）。
"""
import random
import uuid
from typing import List, Optional, Set

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from dao.base import BaseDAO
from models.sticker import Sticker
from models.sticker_favorite import StickerFavorite


STICKER_EMOJIS_BY_NAME = {
    "大笑": "😂", "哈哈": "😄", "开心": "😊", "兴奋": "🤩", "惊喜": "😁",
    "笑哭": "🤣", "眦牙": "😬", "龇牙": "😬", "庆祝": "🥳",
    "难过": "😢", "伤心": "😭", "低落": "😔", "沮丧": "😞", "委屈": "🥹", "哭泣": "😿",
    "生气": "😠", "发怒": "😡", "愤怒": "🤬", "不爽": "😒", "烦躁": "😤",
    "平静": "😐", "无语": "🙄", "疑惑": "🤔", "尴尬": "😅", "冷静": "😑",
    "喜欢": "🥰", "心动": "💓", "亲吻": "😘", "爱你": "❤️", "甜蜜": "💕",
    "温柔": "🥺", "安慰": "🤗", "陪伴": "💙", "理解": "👂",
}


class StickerService(BaseDAO[Sticker]):
    model = Sticker

    @staticmethod
    def fallback_emoji(sticker: Sticker) -> str:
        """图片失效或旧数据重复时使用稳定的单个 emoji。"""
        return STICKER_EMOJIS_BY_NAME.get(sticker.name) or (
            sticker.image_url if not sticker.image_url.startswith(("http://", "https://", "/", "./", "data:", "blob:"))
            else "😊"
        )

    @staticmethod
    def fallback_emoji_simple(name: str, image_url: str) -> str:
        """从名称和 image_url 生成表情（用于 DAO）。"""
        return STICKER_EMOJIS_BY_NAME.get(name) or (
            image_url if image_url and not image_url.startswith(("http://", "https://", "/", "./", "data:", "blob:"))
            else "😊"
        )

    @classmethod
    async def pick_by_emotion(cls, db: AsyncSession, emotion: str) -> Sticker | None:
        """按情绪随机取一个表情包（该情绪没货则回退 neutral）。"""
        stickers = (
            await db.execute(select(Sticker).where(Sticker.emotion == emotion))
        ).scalars().all()
        if not stickers:
            stickers = (
                await db.execute(select(Sticker).where(Sticker.emotion == "neutral"))
            ).scalars().all()
        return random.choice(stickers) if stickers else None

    @classmethod
    async def get(cls, db: AsyncSession, sticker_id: int) -> Sticker | None:
        return (
            await db.execute(select(Sticker).where(Sticker.id == sticker_id))
        ).scalar_one_or_none()

    # ---------------- 收藏（STK-04） ----------------
    @classmethod
    async def favorite(cls, db: AsyncSession, user_id: uuid.UUID, sticker_id: int) -> bool:
        """收藏表情包（幂等）。返回是否已收藏。"""
        exists = (
            await db.execute(
                select(StickerFavorite).where(
                    StickerFavorite.user_id == user_id,
                    StickerFavorite.sticker_id == sticker_id,
                )
            )
        ).scalar_one_or_none()
        if exists:
            return True
        db.add(StickerFavorite(user_id=user_id, sticker_id=sticker_id))
        await db.commit()
        return True

    @classmethod
    async def unfavorite(cls, db: AsyncSession, user_id: uuid.UUID, sticker_id: int) -> bool:
        """取消收藏。返回是否真的删掉了。"""
        result = await db.execute(
            delete(StickerFavorite).where(
                StickerFavorite.user_id == user_id,
                StickerFavorite.sticker_id == sticker_id,
            )
        )
        await db.commit()
        return result.rowcount > 0

    @classmethod
    async def list_favorites(cls, db: AsyncSession, user_id: uuid.UUID) -> List[dict]:
        """我的收藏列表（含表情包信息，按收藏时间倒序）。"""
        stmt = (
            select(Sticker)
            .join(StickerFavorite, StickerFavorite.sticker_id == Sticker.id)
            .where(StickerFavorite.user_id == user_id)
            .order_by(StickerFavorite.created_at.desc())
        )
        stickers = (await db.execute(stmt)).scalars().all()
        return [
            {
                "id": s.id, "name": s.name, "emotion": s.emotion,
                "image_url": s.image_url, "category": s.category,
                "sticker_emoji": cls.fallback_emoji(s),
            }
            for s in stickers
        ]

    @classmethod
    async def get_favorited_ids(cls, db: AsyncSession, user_id: uuid.UUID) -> Set[int]:
        """当前用户已收藏的表情包 id 集合（列表页打 is_favorited 标记用）。"""
        rows = (
            await db.execute(
                select(StickerFavorite.sticker_id).where(StickerFavorite.user_id == user_id)
            )
        ).scalars().all()
        return set(rows)
