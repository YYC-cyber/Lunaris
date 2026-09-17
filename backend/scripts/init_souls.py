# backend/scripts/init_souls.py
"""
初始化 AI 角色种子数据（6 个角色）

v1.2：personality 存 SOUL.md 文件路径，改人设只改 backend/data/souls/{name}/SOUL.md

前置：先跑数据库迁移建表
    cd backend && alembic -c alembic/alembic.ini upgrade head

运行（任选其一）：
    cd backend && python scripts/init_souls.py
    python backend/scripts/init_souls.py
"""
import asyncio
import sys
from pathlib import Path
from typing import TypedDict

# 把 backend/ 加入 sys.path，保证 `config` / `models` 可导入（与运行目录无关）
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select  # noqa: E402

from config.database import AsyncSessionLocal  # noqa: E402
from models.v1_0.soul import Soul  # noqa: E402


class SoulSeed(TypedDict):
    """种子角色结构（personality 为 SOUL.md 文件路径，v1.2）"""
    name: str
    display_name: str
    gender: str
    personality: str
    first_greeting: str
    voice_id: str
    tags: list[str]
    is_default: bool
    sort_order: int


SOULS: list[SoulSeed] = [
    {
        "name": "aiden",
        "display_name": "艾登",
        "gender": "male",
        "personality": "data/souls/aiden/SOUL.md",
        "first_greeting": "你来了。记住——我不爱说好听的，但答应过你的事，一件都不会少。",
        "voice_id": "aiden-deep-male",
        "tags": ["冷酷", "桀骜", "嘴硬心软"],
        "is_default": True,
        "sort_order": 1,
    },
    {
        "name": "caelus",
        "display_name": "凯勒斯",
        "gender": "male",
        "personality": "data/souls/caelus/SOUL.md",
        "first_greeting": "你来了。我这个人不擅长寒暄，但你来找我，我很高兴。慢慢说，我听着。",
        "voice_id": "caelus-deep-male",
        "tags": ["高冷", "理性", "外冷内热"],
        "is_default": False,
        "sort_order": 2,
    },
    {
        "name": "kael",
        "display_name": "凯尔",
        "gender": "male",
        "personality": "data/souls/kael/SOUL.md",
        "first_greeting": "终于等到你了！以后你的事，就是我的事，包在我身上。今天过得怎么样？",
        "voice_id": "kael-bright-male",
        "tags": ["阳光", "直球", "活力满满"],
        "is_default": False,
        "sort_order": 3,
    },
    {
        "name": "diana",
        "display_name": "黛安娜",
        "gender": "female",
        "personality": "data/souls/diana/SOUL.md",
        "first_greeting": "你来了。我正好刚练完琴，正想找人聊聊天呢。",
        "voice_id": "diana-gentle-female",
        "tags": ["知性", "温柔", "艺术气质"],
        "is_default": True,
        "sort_order": 4,
    },
    {
        "name": "raven",
        "display_name": "瑞雯",
        "gender": "female",
        "personality": "data/souls/raven/SOUL.md",
        "first_greeting": "来了？坐吧。先说说你今天过得怎么样，我听着。",
        "voice_id": "raven-cool-female",
        "tags": ["成熟", "干练", "事业型"],
        "is_default": False,
        "sort_order": 5,
    },
    {
        "name": "luna",
        "display_name": "露娜",
        "gender": "female",
        "personality": "data/souls/luna/SOUL.md",
        "first_greeting": "嗨！你终于来啦！我等你好久了~ 今天过得怎么样？",
        "voice_id": "luna-cute-female",
        "tags": ["元气", "有主见", "爱cos"],
        "is_default": False,
        "sort_order": 6,
    },
]


async def init_souls():
    print("🚀 开始插入 AI 角色种子数据...")
    async with AsyncSessionLocal() as db:
        for data in SOULS:
            # 校验 SOUL.md 是否存在（personality 存的是文件路径）
            md_path = BACKEND_DIR / data["personality"]
            if not md_path.exists():
                print(f"⚠️  警告：{data['display_name']} 的 SOUL.md 不存在：{md_path}")

            # 幂等：按 name 判重
            exists = (
                await db.execute(select(Soul).where(Soul.name == data["name"]))
            ).scalar_one_or_none()
            if exists:
                print(f"⏭️  {data['display_name']} ({data['name']}) 已存在，跳过")
                continue

            db.add(Soul(**data))
            print(f"✅ 插入 {data['display_name']} ({data['name']})")

        await db.commit()
        print("🎉 所有种子数据插入完成！")


if __name__ == "__main__":
    asyncio.run(init_souls())
