"""
初始化表情包种子数据（STK-04）

前置：先跑数据库迁移建表
    cd backend && alembic -c alembic/alembic.ini upgrade head

运行（任选其一）：
    cd backend && python scripts/init_stickers.py
    python backend/scripts/init_stickers.py
"""
import asyncio
import sys
from pathlib import Path
from typing import TypedDict

# 把 backend/ 加入 sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select  # noqa: E402
from config.database import AsyncSessionLocal  # noqa: E402
from models.sticker import Sticker  # noqa: E402


class StickerSeed(TypedDict):
    """表情包种子结构"""
    name: str
    emotion: str
    image_url: str
    category: str
    sort_order: int


# 6 组情绪 × 多种表情。每个 emoji 均唯一，避免选择面板中出现重复内容。
STICKERS: list[StickerSeed] = [
    # ===== happy 开心 =====
    {"name": "大笑", "emotion": "happy", "image_url": "😂", "category": "开心", "sort_order": 1},
    {"name": "哈哈", "emotion": "happy", "image_url": "😄", "category": "开心", "sort_order": 2},
    {"name": "开心", "emotion": "happy", "image_url": "😊", "category": "开心", "sort_order": 3},
    {"name": "兴奋", "emotion": "happy", "image_url": "🤩", "category": "开心", "sort_order": 4},
    {"name": "惊喜", "emotion": "happy", "image_url": "😁", "category": "开心", "sort_order": 5},
    {"name": "笑哭", "emotion": "happy", "image_url": "🤣", "category": "开心", "sort_order": 6},

    # ===== sad 难过 =====
    {"name": "难过", "emotion": "sad", "image_url": "😢", "category": "难过", "sort_order": 7},
    {"name": "伤心", "emotion": "sad", "image_url": "😭", "category": "难过", "sort_order": 8},
    {"name": "低落", "emotion": "sad", "image_url": "😔", "category": "难过", "sort_order": 9},
    {"name": "沮丧", "emotion": "sad", "image_url": "😞", "category": "难过", "sort_order": 10},
    {"name": "委屈", "emotion": "sad", "image_url": "🥹", "category": "难过", "sort_order": 11},

    # ===== angry 生气 =====
    {"name": "生气", "emotion": "angry", "image_url": "😠", "category": "生气", "sort_order": 12},
    {"name": "发怒", "emotion": "angry", "image_url": "😡", "category": "生气", "sort_order": 13},
    {"name": "愤怒", "emotion": "angry", "image_url": "🤬", "category": "生气", "sort_order": 14},
    {"name": "不爽", "emotion": "angry", "image_url": "😒", "category": "生气", "sort_order": 15},
    {"name": "烦躁", "emotion": "angry", "image_url": "😤", "category": "生气", "sort_order": 16},

    # ===== neutral 平静 =====
    {"name": "平静", "emotion": "neutral", "image_url": "😐", "category": "平静", "sort_order": 17},
    {"name": "无语", "emotion": "neutral", "image_url": "🙄", "category": "平静", "sort_order": 18},
    {"name": "疑惑", "emotion": "neutral", "image_url": "🤔", "category": "平静", "sort_order": 19},
    {"name": "尴尬", "emotion": "neutral", "image_url": "😅", "category": "平静", "sort_order": 20},
    {"name": "冷静", "emotion": "neutral", "image_url": "😑", "category": "平静", "sort_order": 21},

    # ===== love 爱意 =====
    {"name": "喜欢", "emotion": "love", "image_url": "🥰", "category": "爱意", "sort_order": 22},
    {"name": "心动", "emotion": "love", "image_url": "💓", "category": "爱意", "sort_order": 23},
    {"name": "亲吻", "emotion": "love", "image_url": "😘", "category": "爱意", "sort_order": 24},
    {"name": "爱你", "emotion": "love", "image_url": "❤️", "category": "爱意", "sort_order": 25},
    {"name": "甜蜜", "emotion": "love", "image_url": "💕", "category": "爱意", "sort_order": 26},

    # ===== gentle 温柔（可选 6 种情绪中加入） =====
    {"name": "温柔", "emotion": "gentle", "image_url": "🥺", "category": "温柔", "sort_order": 27},
    {"name": "安慰", "emotion": "gentle", "image_url": "🤗", "category": "温柔", "sort_order": 28},
    {"name": "陪伴", "emotion": "gentle", "image_url": "💙", "category": "温柔", "sort_order": 29},
    {"name": "理解", "emotion": "gentle", "image_url": "👂", "category": "温柔", "sort_order": 30},
]


async def init_stickers():
    print("🚀 开始插入表情包种子数据...")
    async with AsyncSessionLocal() as db:
        for data in STICKERS:
            # 幂等：按 name + emotion 判重
            exists = (
                await db.execute(
                    select(Sticker).where(
                        Sticker.name == data["name"],
                        Sticker.emotion == data["emotion"],
                    )
                )
            ).scalar_one_or_none()
            if exists:
                for key, value in data.items():
                    setattr(exists, key, value)
                print(f"♻️  更新 {data['name']} ({data['emotion']})")
            else:
                db.add(Sticker(**data))
                print(f"✅ 插入 {data['name']} ({data['emotion']})")

        await db.commit()
        print("🎉 所有表情包种子数据插入完成！")


if __name__ == "__main__":
    asyncio.run(init_stickers())
