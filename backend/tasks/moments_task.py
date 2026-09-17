"""
朋友圈定时任务 —— 框架占位，按注释实现。

【职责】
- publish_moments()
  每天 08:00 / 20:00 执行（MOM-01）：
  1. 拉取今日热点（hotspot_client）
  2. 遍历所有活跃角色，逐个：
     - 调 DeepSeek 生成「温暖治愈」朋友圈文案 + 图片提示词（JSON 输出）
     - 生成/获取配图（image_client，失败兜底）
     - 可选合成 10 秒语音（P2）
     - 落库 moments → notify_service 推送 MomentEvent

【容错】单个角色失败不影响其它角色；失败记日志
"""
# backend/tasks/moments_task.py
"""
朋友圈定时任务：每天早 8 / 晚 8 自动发动态

【职责】
- 为每个活跃角色生成一条朋友圈动态
- 调用 LLM 生成文案（符合角色人设）
- 调用 ImageClient 生成配图
- 写入 moments 表

【触发方式】
由 scheduler.py 每天 08:00 和 20:00 调用
"""

import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import AsyncSessionLocal
from models.v1_0.soul import Soul
from models.v1_0.moment import Moment
from clients.llm_client import LLMClient
from clients.image_client import get_image_client
from services.v1_0.context_service import load_soul_prompt


async def generate_moment_for_soul(
    db: AsyncSession,
    soul_id: int,
) -> Dict[str, Any]:
    """
    为单个角色生成一条动态（含文案 + 配图 + 话题标签）
    核心思路：用角色的人设（SOUL.md）直接驱动生成，保证内容高度个性化
    """
    # 1. 获取角色信息
    stmt = select(Soul).where(Soul.id == soul_id)
    result = await db.execute(stmt)
    soul = result.scalar_one_or_none()
    if not soul:
        return {"success": False, "error": f"角色 {soul_id} 不存在"}

    # 2. 获取角色人设（复用 context_service 的 SoulPromptLoader）
    system_prompt = await load_soul_prompt(db, soul_id)

    # 3. 调用 LLM 生成朋友圈文案
    llm = LLMClient()
    now = datetime.now()
    time_desc = "早上" if now.hour < 12 else ("下午" if now.hour < 18 else "晚上")

    # 文案生成 prompt —— 强调用人设生成
    content_prompt = (
        f"你现在要发一条朋友圈动态。\n"
        f"当前时间是{time_desc}。\n"
        f"\n【核心要求】\n"
        f"1. 这条朋友圈必须充分体现你的个性、特点、品味和生活风格\n"
        f"2. 不要发通用的「心情不错」这种文案，要有你特有的见解或故事\n"
        f"3. 可以涉及你的爱好、观点、生活片段，让人一看就知道是你\n"
        f"4. 口吻要自然真实，像真人发朋友圈\n"
        f"5. 不超过 100 字\n"
        f"6. 结尾带 1-2 个话题标签（选择真的相关的，如 #夜晚 #思考 #日常 等）\n"
        f"7. 禁止括号动作描写，禁止提自己是 AI\n"
        f"\n【例子】\n"
        f"- ❌ 不好：「今天天气很好，心情不错。#日常」（太通用）\n"
        f"- ✅ 好：「又是一个失眠夜。不过和你聊天让我忘了闹心事。感谢。#夜晚 #陪伴」（有个性、有故事）\n"
        f"\n请直接输出朋友圈内容，不要其他说明。"
    )

    try:
        content = await llm.chat_completion(
            system_prompt=system_prompt,
            history=[],
            user_message=content_prompt,
            temperature=0.95,  # 提高创意度，让每个角色的回复更不同
            max_tokens=200,
        )
        content = content.strip()
    except Exception as e:
        print(f"⚠️ 文案生成失败 (soul {soul_id}): {e}")
        # 兜底文案保持个性
        fallback_templates = {
            ("male", "early"): "清晨就想着又要开始一天了。",
            ("male", "afternoon"): "下午的某个瞬间，想到了你。",
            ("male", "evening"): "又是一个深夜。",
            ("female", "early"): "早上起床第一反应，又是新的一天。",
            ("female", "afternoon"): "下午的阳光刚刚好。",
            ("female", "evening"): "夜晚，一个人待着也挺好的。",
        }
        time_key = "early" if now.hour < 12 else ("afternoon" if now.hour < 18 else "evening")
        content = fallback_templates.get((soul.gender, time_key), f"{time_desc}，想你了。")
        content += " #日常"

    # 4. 提取话题标签（从文案中提取 #xxx）
    tags = []
    for word in content.split():
        if word.startswith("#") and len(word) > 1:
            tags.append(word[1:])

    # 5. 生成配图描述 → 调用图片生成（更个性化）
    # 根据角色名+话题+时间生成更贴切的图片提示
    personality_hint = ""
    if soul.display_name == "艾登":
        personality_hint = "深色系、夜晚、神秘感、冷酷气质、夜钓、黑胶唱片、黑色机能服装"
    elif soul.display_name == "凯勒斯":
        personality_hint = "温柔、知性、书籍、咖啡、柔和光线、优雅气质"
    elif soul.display_name == "凯尔":
        personality_hint = "热血、阳光、运动、活力、明亮感、坚定眼神"
    elif soul.display_name == "黛安娜":
        personality_hint = "神秘、优雅、星辰、魔法感、紫色系、高级感"
    elif soul.display_name == "露娜":
        personality_hint = "温暖、甜蜜、治愈、柔软、暖色系、陪伴感"
    elif soul.display_name == "瑞雯":
        personality_hint = "率真、坚强、野性、独立、鲜艳色彩、自信气质"
    else:
        personality_hint = f"{soul.display_name}的个性特征和生活风格"

    topic_hint = f"#{'关于' + tags[0] if tags else '日常'}"
    image_prompt = f"一张{time_desc}的真人朋友圈配图，体现{personality_hint}，{topic_hint}，柔和光线，生活气息，高级感"

    image_client = get_image_client()
    image_url = await image_client.generate(image_prompt)

    # 6. 存入数据库
    moment = Moment(
        soul_id=soul_id,
        content=content,
        images=[image_url] if image_url else [],
        topic_tags=tags or ["日常"],
        is_ai_generated=True,
        like_count=0,
    )
    db.add(moment)
    await db.flush()

    return {
        "success": True,
        "moment_id": moment.id,
        "content": content,
        "tags": tags,
        "image_url": image_url,
        # 供 commit 后推送给用户
        "moment_data": {
            "id": moment.id,
            "soul_id": soul_id,
            "content": content,
            "images": moment.images or [],
            "topic_tags": tags or ["日常"],
            "created_at": moment.created_at.isoformat() if moment.created_at else datetime.now().isoformat(),
        },
    }


async def run_moments_task() -> None:
    """
    定时任务入口：为所有活跃角色生成朋友圈动态
    每天 08:00 和 20:00 由 scheduler 调用
    """
    print(f"📱 朋友圈定时任务开始执行: {datetime.now()}")

    created_moments = []
    success_count = 0
    fail_count = 0

    async with AsyncSessionLocal() as db:
        # 获取所有角色
        souls = (await db.execute(select(Soul).order_by(Soul.id))).scalars().all()
        print(f"📱 共 {len(souls)} 个角色，开始发动态...")

        for soul in souls:
            try:
                # 每个角色独立执行，一个失败不影响其他
                result = await generate_moment_for_soul(db, soul.id)
                if result["success"]:
                    success_count += 1
                    created_moments.append(result["moment_data"])
                    print(f"✅ {soul.display_name} 发动态成功: {result['content'][:30]}...")
                else:
                    fail_count += 1
                    print(f"❌ {soul.display_name} 发动态失败: {result.get('error', '未知错误')}")
            except Exception as e:
                fail_count += 1
                print(f"❌ {soul.display_name} 发动态失败: {e}")

        await db.commit()

    # ⚠️ commit 之后再推送：避免推了「未落库」的动态
    if created_moments:
        from models.user import User
        from services.notify_service import push_moment

        async with AsyncSessionLocal() as db:
            all_users = (await db.execute(select(User))).scalars().all()
        user_ids = [str(u.id) for u in all_users]

        # 简化版：推给所有注册用户（后续可按「配对/关注关系」细化，只推相关用户）
        for moment_data in created_moments:
            for user_id in user_ids:
                await push_moment(user_id=user_id, moment_data=moment_data)
        print(f"📦 已推送 {len(created_moments)} 条动态给 {len(user_ids)} 个用户")

    print(f"📱 朋友圈任务完成: 成功 {success_count}，失败 {fail_count}")


# 测试入口（用于手动测试）
if __name__ == "__main__":
    asyncio.run(run_moments_task())