"""
StickerFavorite 模型 —— sticker_favorites 表（表情包收藏，STK-04）。

【字段】
- id          SERIAL    PRIMARY KEY
- user_id     UUID      收藏用户
- sticker_id  INT       收藏的表情包
- created_at  TIMESTAMP DEFAULT NOW()
- UNIQUE(user_id, sticker_id)   # 同一表情包只收藏一次
"""
from sqlalchemy import Column, DateTime, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as UUID_PG

from config.database import Base


class StickerFavorite(Base):
    __tablename__ = "sticker_favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID_PG(as_uuid=True), nullable=False, index=True)
    sticker_id = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "sticker_id", name="uq_user_sticker"),
    )
