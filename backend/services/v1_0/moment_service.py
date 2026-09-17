"""
MomentService —— 朋友圈业务 —— 框架占位，按注释实现。

【职责】
- publish(soul)             # 定时任务调用：热点→文案→配图→落库→推送
  - 拉取今日热点（hotspot_client）
  - 调 DeepSeek 生成文案 + 图片提示词（JSON 输出）
  - 生成/获取配图（image_client，失败降级兜底图）
  - 可选合成语音（tts_client）
  - 落库 moments → notify_service.push(MomentEvent)
- timeline(user, cursor)    # 时间倒序分页，填充 is_liked / soul_name
- like(user, moment_id) / unlike(user, moment_id)
- comment(user, moment_id, content)
  - 落库评论 → 后台异步生成 AI 评论区回复（楼中楼）
- delete_comment(user, comment_id)

【说明】
- publish 由 tasks/moments_task 每天 08/20 触发
- 用户侧点赞表可后续单独建（当前用计数冗余 + is_liked 聚合）
"""
# backend/services/moment_service.py
import asyncio
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, and_, exists

from models.v1_0.moment import Moment
from models.v1_0.comment import Comment
from models.v1_0.like import Like
from models.v1_0.soul import Soul
from models.v1_0.friendship import Friendship
from clients.llm_client import LLMClient
from common.helpers import intimacy_stage
from services.v1_0.context_service import load_soul_prompt, prohibitions
from config.database import AsyncSessionLocal
from config.settings import get_settings

settings = get_settings()


class MomentService:
    # ---------- 用户发布 (P0 新增) ----------
    @staticmethod
    async def publish(
        db: AsyncSession,
        user_id: uuid.UUID,
        content: str,
        images: Optional[List[str]] = None,
        topic_tags: Optional[List[str]] = None,
        visibility: str = "public",
        visible_groups: Optional[List[str]] = None,
        hidden_user_ids: Optional[List[str]] = None,
    ) -> Moment:
        """用户发布新动态"""
        from dao.v1_0.moment_dao import MomentDAO

        # 自动从内容提取 # 标签
        if not topic_tags:
            topic_tags = [tag[1:] for tag in content.split() if tag.startswith("#")]

        return await MomentDAO.create_user_moment(
            db,
            user_id=user_id,
            content=content,
            images=images or [],
            topic_tags=topic_tags,
            visibility=visibility,
            visible_groups=visible_groups or [],
            hidden_user_ids=hidden_user_ids or [],
        )

    @staticmethod
    async def delete_moment(db: AsyncSession, moment_id: int, user_id: uuid.UUID) -> bool:
        """软删除用户自己的动态（仅所有者可删，DB-03）

        软删除：标记 is_deleted=True + deleted_at，数据保留可恢复。
        评论和点赞数据不物理删除（符合数据保留要求）。
        """
        from dao.v1_0.moment_dao import MomentDAO
        from sqlalchemy import update
        from models.v1_0.moment import Moment
        from datetime import datetime

        moment = await MomentDAO.get_owned(db, moment_id, user_id)
        if not moment:
            return False

        try:
            async with db.begin():
                await db.execute(
                    update(Moment)
                    .where(Moment.id == moment_id)
                    .values(is_deleted=True, deleted_at=datetime.utcnow())
                )
            return True
        except Exception:
            return False

    @staticmethod
    async def update_visibility(
        db: AsyncSession,
        moment_id: int,
        user_id: uuid.UUID,
        visibility: str,
        visible_groups: Optional[List[str]] = None,
        hidden_user_ids: Optional[List[str]] = None,
    ) -> Optional[Moment]:
        """更新动态隐私设置（仅所有者可改）"""
        from dao.v1_0.moment_dao import MomentDAO

        moment = await MomentDAO.get_owned(db, moment_id, user_id)
        if not moment:
            return None

        moment.visibility = visibility
        if visible_groups is not None:
            moment.visible_groups = visible_groups
        if hidden_user_ids is not None:
            moment.hidden_user_ids = hidden_user_ids
        db.add(moment)
        await db.commit()
        await db.refresh(moment)
        return moment

    # ---------- 时间线 ----------
    @staticmethod
    async def get_timeline(
        db: AsyncSession,
        user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """获取朋友圈时间线（含点赞状态和评论）"""
        stmt = select(Moment).order_by(desc(Moment.created_at)).offset(offset).limit(limit)
        result = await db.execute(stmt)
        moments = result.scalars().all()

        # 批量查询每个动态的点赞状态和评论
        result_list = []
        for m in moments:
            # 当前用户是否点赞
            liked = await db.execute(
                select(exists().where(Like.moment_id == m.id, Like.user_id == user_id))
            )
            is_liked = liked.scalar()

            # 获取 soul 名称
            soul_name = None
            if m.soul_id:
                soul_stmt = select(Soul).where(Soul.id == m.soul_id)
                soul_result = await db.execute(soul_stmt)
                soul = soul_result.scalar_one_or_none()
                if soul:
                    soul_name = soul.display_name or soul.name

            # 评论列表（按时间正序，取最近 5 条）
            comments_stmt = (
                select(Comment)
                .where(Comment.moment_id == m.id)
                .order_by(Comment.created_at.asc())
                .limit(5)
            )
            comments_result = await db.execute(comments_stmt)
            comments = comments_result.scalars().all()

            result_list.append({
                "id": m.id,
                "soul_id": m.soul_id,
                "soul_name": soul_name,  # 添加角色名称
                "content": m.content,
                "images": m.images or [],          # 裸 SQL 插入可能为 NULL，兜底为空数组
                "topic_tags": m.topic_tags or [],  # 同上
                "voice_url": m.voice_url,
                "is_ai_generated": m.is_ai_generated is not False,  # NULL → True
                "like_count": m.like_count or 0,                    # NULL → 0
                "created_at": m.created_at.isoformat(),
                "is_liked": is_liked,
                "comments": [
                    {
                        "id": c.id,
                        "user_id": str(c.user_id) if c.user_id else None,
                        "soul_id": c.soul_id,
                        "parent_comment_id": c.parent_comment_id,
                        "content": c.content,
                        "created_at": c.created_at.isoformat(),
                        "is_ai": c.user_id is None,  # AI 回复标记
                    }
                    for c in comments
                ],
            })
        return result_list

    # ---------- 点赞 ----------
    @staticmethod
    async def toggle_like(db: AsyncSession, moment_id: int, user_id: uuid.UUID) -> bool:
        """返回 True=已点赞，False=已取消"""
        # 检查是否已点赞
        stmt = select(Like).where(Like.moment_id == moment_id, Like.user_id == user_id)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # 取消点赞
            await db.delete(existing)
            await db.execute(
                Moment.__table__.update()
                .where(Moment.id == moment_id)
                .values(like_count=Moment.like_count - 1)
            )
            await db.commit()
            return False
        else:
            # 点赞
            like = Like(moment_id=moment_id, user_id=user_id)
            db.add(like)
            await db.execute(
                Moment.__table__.update()
                .where(Moment.id == moment_id)
                .values(like_count=Moment.like_count + 1)
            )
            await db.commit()
            return True

    # ---------- 评论 ----------
    @staticmethod
    async def add_comment(
        db: AsyncSession,
        moment_id: int,
        user_id: uuid.UUID,
        content: str,
        parent_comment_id: Optional[int] = None,
    ) -> Comment:
        """用户评论（触发 AI 回复）"""
        comment = Comment(
            moment_id=moment_id,
            user_id=user_id,
            soul_id=None,
            parent_comment_id=parent_comment_id,
            content=content,
        )
        db.add(comment)
        await db.flush()

        # 获取动态对应的 soul_id
        stmt = select(Moment).where(Moment.id == moment_id)
        result = await db.execute(stmt)
        moment = result.scalar_one_or_none()

        # 后台异步触发 AI 评论区回复（不阻塞）
        if moment:
            asyncio.create_task(
                MomentService._generate_ai_comment_reply(
                    moment_id=moment_id,
                    soul_id=moment.soul_id,
                    user_comment_id=comment.id,
                    user_content=content,
                    parent_comment_id=parent_comment_id,
                )
            )

        await db.commit()
        await db.refresh(comment)
        return comment

    # ---------- AI 评论区回复（后台任务） ----------
    @staticmethod
    async def _generate_ai_comment_reply(
        moment_id: int,
        soul_id: int,
        user_comment_id: int,
        user_content: str,
        parent_comment_id: Optional[int] = None,
    ) -> None:
        """
        后台任务：生成 AI 对评论区某条评论的回复（楼中楼）。
        必须使用独立 DB 会话（请求会话在响应后已关闭，不能复用），失败不影响主流程。
        """
        try:
            async with AsyncSessionLocal() as db:
                # 1. 获取角色信息
                soul_stmt = select(Soul).where(Soul.id == soul_id)
                soul = (await db.execute(soul_stmt)).scalar_one_or_none()
                if not soul:
                    return

                # 2. 获取亲密度阶段
                friend_stmt = select(Friendship).where(Friendship.soul_id == soul_id)
                friendship = (await db.execute(friend_stmt)).scalar_one_or_none()
                intimacy = friendship.intimacy_level if friendship else 0
                stage, _ = MomentService._stage_info(intimacy)

                # 3. 获取动态内容
                moment_stmt = select(Moment).where(Moment.id == moment_id)
                moment = (await db.execute(moment_stmt)).scalar_one_or_none()
                if not moment:
                    return

                # 4. 构建系统提示（复用 context_service 的人设加载 + 通用禁令）
                system_prompt = await load_soul_prompt(db, soul_id)
                prohibition_text = prohibitions()
                stage_desc = f"当前关系阶段：{stage}。按此阶段分寸回复。"
                full_prompt = system_prompt + "\n\n" + stage_desc + "\n\n" + prohibition_text

                # 5. 调用 LLM 生成回复
                llm = LLMClient()
                user_msg = (
                    f"用户在你的朋友圈动态下评论了：\n"
                    f"动态内容：{moment.content}\n"
                    f"用户评论：{user_content}\n"
                    f"请用你的口吻回复这条评论，简短、自然、口语化，像真人朋友一样。"
                )
                ai_reply = await llm.chat_completion(
                    system_prompt=full_prompt,
                    history=[],
                    user_message=user_msg,
                    temperature=0.8,
                    max_tokens=150,
                )

                if not ai_reply:
                    return

                # 6. 存为 AI 评论（楼中楼）
                ai_comment = Comment(
                    moment_id=moment_id,
                    user_id=None,
                    soul_id=soul_id,
                    parent_comment_id=user_comment_id,  # 直接回复用户那条评论
                    content=ai_reply,
                )
                db.add(ai_comment)
                await db.commit()
                print(f"✅ AI 评论区回复已保存: {ai_reply[:30]}...")

        except Exception as e:
            print(f"⚠️ AI 评论区回复失败: {e}")

    @staticmethod
    def _stage_info(intimacy: int):
        # 阈值来自 common.constants（单一来源）
        stage = intimacy_stage(intimacy)
        descs = {"初识": "客气礼貌", "熟悉": "自然开玩笑", "亲密": "随意交心", "挚爱": "毫无顾忌"}
        return stage, descs[stage]