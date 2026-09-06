# backend/services/chat_service.py
"""聊天服务：组装上下文 → 调用 LLM → 落库 → 更新亲密度与记忆。

亲密度成长规则落地自 backend/data/scenes/SCENE_FRAMEWORK.md：
- 有效对话才加分（过短 / 纯语气词不加，防刷）
- 每日每角色上限 +3
- 越接近挚爱升得越慢（初识/熟悉 +1，亲密 +0.5，挚爱 +0.2）
"""
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from clients.llm_client import LLMClient
from config.database import AsyncSessionLocal
from config.logging_config import get_logger
from dao.friendship_dao import FriendshipDAO
from dao.message_dao import MessageDAO
from dao.soul_dao import SoulDAO
from models.friendship import Friendship
from models.message import Message
from services import context_service
from services.sticker_service import StickerService

logger = get_logger("chat_service")

# ==================== 亲密度成长（SCENE_FRAMEWORK 落地） ====================
_DAILY_INTIMACY_CAP = 3  # 每日上限
# 当日已加分计数：key=(user_id, soul_id, yyyy-mm-dd) → 次数
# ⚠️ 进程内存实现：重启即清零。多实例/持久化后续接 Redis 或 DB 表。
_intimacy_counts: Dict[tuple, int] = {}
# LLM 失败时的兜底回复（据此判断是否跳过记忆提取）
_FALLBACK_REPLY = "（我暂时无法回答，请稍后再试）"
# 带原因的错误回复前缀（以它开头视为错误，跳过记忆/TTS）
_LLM_ERROR_PREFIX = "（AI 服务出错了："
# 持有后台记忆任务引用，防止被垃圾回收
_memory_tasks: set = set()
_FILLER_INPUTS = {
    "嗯", "哦", "啊", "好", "哈", "嗯嗯", "哦哦", "哈哈", "呵呵",
    "好的", "知道了", "行", "ok", "OK", "。。", "。。。",
}


def clean_generated_text(text: str) -> str:
    """移除模型输出中的 SSML 和内部等待参数，避免控制文本进入 TTS。"""
    import re

    cleaned = re.sub(r"<[^>]*>", "", text or "")
    cleaned = re.sub(
        r"(?<![A-Za-z])(?:wait(?:time)?|break(?:time)?|time)\s*[:=]\s*[\d.]+\s*(?:ms|s|sec|secs|seconds)?(?![A-Za-z])",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\b(?:break|wait)\s+time\s+is\s+(?:about\s+)?[\d.]+\s+"
        r"(?:ms|s|sec|secs|second|seconds)\b[.!?]?",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return re.sub(r"[ \t]{2,}", " ", cleaned).strip()


def _today_str() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d")


def _is_meaningful(content: str) -> bool:
    """有效对话判定：过短或纯语气词不算（防刷亲密度）。"""
    trimmed = content.strip()
    if not trimmed or len(trimmed) < 2:
        return False
    if trimmed in _FILLER_INPUTS:
        return False
    return True


class ChatService:
    CONTEXT_WINDOW = 20

    # ---------------- 亲密度成长 ----------------
    @staticmethod
    def _intimacy_growth(intimacy: int) -> float:
        """按当前阶段决定单次成长：越亲密升得越慢。"""
        if intimacy < 50:
            return 1.0
        if intimacy < 75:
            return 0.5
        return 0.2

    @staticmethod
    def _can_grow_today(user_id, soul_id) -> bool:
        key = (str(user_id), soul_id, _today_str())
        return _intimacy_counts.get(key, 0) < _DAILY_INTIMACY_CAP

    @staticmethod
    def _mark_grown_today(user_id, soul_id) -> None:
        key = (str(user_id), soul_id, _today_str())
        _intimacy_counts[key] = _intimacy_counts.get(key, 0) + 1

    @staticmethod
    async def _make_llm(db: AsyncSession, user_id: uuid.UUID) -> LLMClient | None:
        """按用户 API 配置创建 LLM 客户端。

        无有效 Key（未配置且未授权）→ 返回 None，调用方给出「未配置/未授权」提示，而非回退全局。
        """
        from services.api_config_service import ApiConfigService
        cfg = await ApiConfigService.resolve(db, user_id, "llm")
        if not cfg.get("api_key"):
            return None
        return LLMClient(api_key=cfg["api_key"], base_url=cfg.get("base_url"), model=cfg.get("model"))

    # ---------------- 上下文构建 ----------------
    @staticmethod
    async def get_conversation_history(
        db: AsyncSession,
        user_id: uuid.UUID,
        soul_id: int,
        limit: int = CONTEXT_WINDOW,
    ) -> List[Dict[str, str]]:
        messages = await MessageDAO.list_by_soul(db, user_id, soul_id, limit)
        messages.reverse()

        history = []
        for msg in messages:
            role = "user" if msg.sender_type == "user" else "assistant"
            content = msg.content

            # 如果是表情包，增强文本描述让 AI 理解（LLM 不支持图像，用文字描述表情）
            if msg.msg_type == "sticker" and msg.sticker_id:
                from dao.sticker_dao import StickerDAO
                sticker = await StickerDAO.get(db, msg.sticker_id)
                if sticker:
                    # 生成格式：[表情: 名字 (情绪)]，如 [表情: 伤心 (sad)]
                    content = f"[表情: {sticker.name} ({sticker.emotion})]"

            # 如果是用户发的图片，提示 AI（DeepSeek 暂不支持图像理解，需要用户描述）
            elif msg.msg_type == "image":
                content = f"[用户上传了一张图片]{msg.content or '（无描述）'}"

            history.append({"role": role, "content": content})
        return history

    @staticmethod
    async def get_group_conversation_history(
        db: AsyncSession,
        group_id: int,
        limit: int = 20,
    ) -> List[Dict[str, str]]:
        """获取群聊历史，带发言者标记（用于 AI 理解群聊上下文）

        格式：[发言者名字]: 内容
        """
        from dao.group_chat_dao import GroupMessageDAO
        from dao.soul_dao import SoulDAO
        from dao.user_dao import UserDAO

        messages = await GroupMessageDAO.list_messages(db, group_id, limit=limit)

        history = []
        for msg in messages:
            role = "user" if msg.sender_type == "user" else "assistant"

            # 获取发言者名字
            if msg.sender_type == "ai":
                soul = await SoulDAO.get(db, msg.soul_id)
                sender_name = soul.display_name if soul else "Unknown"
            else:
                user = await UserDAO.get(db, msg.sender_id)
                sender_name = user.nickname if user else "Unknown"

            # 格式化：[名字]: 内容
            content = f"[{sender_name}]: {msg.content}"

            history.append({"role": role, "content": content})

        return history


    @staticmethod
    def _schedule_tts(ai_msg_id: int, soul_id: int, content: str, emotion: str = "neutral", intimacy: int = 0) -> None:
        """后台合成 AI 语音（CHAT-04）：用角色性格音色/语速，写回 message.voice_url。

        调用判断 LLM 判断是否需要生成语音。
        """

        async def _run():
            try:
                async with AsyncSessionLocal() as db:
                    should_voice = await ChatService._should_synthesize_voice(
                        db, content, emotion, intimacy
                    )

                if not should_voice:
                    return

                async with AsyncSessionLocal() as db:
                    soul = await SoulDAO.get(db, soul_id)
                    from clients.tts_client import TTSClient
                    url = await TTSClient().synthesize(
                        content, emotion,
                        voice=soul.tts_voice if soul else None,
                        rate=soul.tts_rate if soul else None,
                    )
                    ai_msg = await MessageDAO.get(db, ai_msg_id)
                    if ai_msg:
                        await MessageDAO.update(db, ai_msg, voice_url=url)
            except Exception as e:
                logger.warning(f"TTS 合成失败: {e}", exc_info=True)

        task = asyncio.create_task(_run())
        _memory_tasks.add(task)
        task.add_done_callback(_memory_tasks.discard)

    @staticmethod
    async def _synthesize_tts_for_message(
        db: AsyncSession,
        ai_msg: Message,
        soul_id: int,
        content: str,
        emotion: str = "neutral",
        intimacy: int = 0,
    ) -> str | None:
        """合成 AI 语音并写回当前消息；失败不影响文字回复。

        【语音生成决策】
        调用 LLM 判断是否适合语音，避免所有回复都转语音。
        """
        # 调用判断 LLM
        should_voice = await ChatService._should_synthesize_voice(
            db, content, emotion, intimacy
        )

        if not should_voice:
            return None

        try:
            from clients.tts_client import TTSClient

            soul = await SoulDAO.get(db, soul_id)
            url = await TTSClient().synthesize(
                content,
                emotion,
                voice=soul.tts_voice if soul else None,
                rate=soul.tts_rate if soul else None,
            )
            await MessageDAO.update(db, ai_msg, voice_url=url)
            return url
        except Exception as e:
            logger.warning(f"TTS 合成失败: {e}", exc_info=True)
            return None

    @staticmethod
    async def _should_synthesize_voice(
        db: AsyncSession,
        content: str,
        emotion: str,
        intimacy: int,
    ) -> bool:
        """判断是否应该生成语音。

        触发规则（宽松模式 - 默认生成）：
        - 消息长度 >= 4 字符：生成语音（自然对话都会用语音）
        - 太短的消息（"好的" "对" "嗯"）：不转语音，节省时间
        """
        # 最小长度检查：太短就不转（如"好的" "对" "嗯"）
        if not content or len(content) < 4:
            return False

        # 所有其他情况都转语音
        return True




    # ---------------- 主流程 ----------------
    @staticmethod
    async def send_message(
        db: AsyncSession,
        user_id: uuid.UUID,
        soul_id: int,
        content: str,
        sticker_id: int | None = None,
        voice_url: str | None = None,  # 用户发的语音 URL
    ) -> Dict[str, Any]:
        # 1. 存储用户消息（支持纯表情包 + 语音，但不支持用户发图片给AI）
        user_sticker = await StickerService.get(db, sticker_id) if sticker_id else None

        # 确定消息类型和内容
        if user_sticker:
            msg_type = "sticker"
        elif voice_url:
            msg_type = "voice"
        else:
            msg_type = "text"

        msg_content = content or (user_sticker.name if user_sticker else "")

        user_msg = await MessageDAO.create(
            db,
            user_id=user_id,
            soul_id=soul_id,
            sender_type="user",
            content=msg_content,
            msg_type=msg_type,
            sticker_id=sticker_id,
            voice_url=voice_url,  # 保存用户的语音 URL
        )

        # 1.5 危机检测（SAFE）：命中走危机流程（不调 LLM、不记记忆、不合成语音）
        from core.crisis import CrisisService
        crisis_hit = await CrisisService.detect(content)
        if crisis_hit:
            ai_response = await CrisisService.handle_crisis(
                db, user_id, soul_id, user_msg.id, content, crisis_hit
            )
            ai_msg = await MessageDAO.create(
                db, user_id=user_id, soul_id=soul_id, sender_type="ai",
                content=ai_response, emotion="gentle",
            )
            await db.commit()
            return {
                "user_message_id": user_msg.id,
                "ai_message_id": ai_msg.id,
                "content": ai_response,
                "emotion": "gentle",
                "created_at": ai_msg.created_at.isoformat() if ai_msg.created_at else "",
                "reply_sticker": None,
            }

        # 1.6 内容安全（非功能）：敏感词（本地）+ 可选语义（DeepSeek，默认关）
        if content:
            from core.audit_log import log_audit
            from core.security import scan_semantic, scan_text
            from config.settings import get_settings
            _scan = await scan_text(content)
            _semantic_ok = True
            if _scan.is_passed and get_settings().ENABLE_SEMANTIC_SCAN:
                _semantic_ok = (await scan_semantic(content)).get("is_passed", True)
            if not _scan.is_passed or not _semantic_ok:
                await log_audit(
                    db, user_id, "content_blocked",
                    {"content": content[:200], "keywords": getattr(_scan, "hit_keywords", [])},
                    risk_level="high",
                )
                blocked_reply = "（这个内容我不太方便回应，我们聊点别的吧）"
                ai_msg = await MessageDAO.create(
                    db, user_id=user_id, soul_id=soul_id, sender_type="ai",
                    content=blocked_reply, emotion="neutral",
                )
                await db.commit()
                return {
                    "user_message_id": user_msg.id,
                    "ai_message_id": ai_msg.id,
                    "content": blocked_reply,
                    "emotion": "neutral",
                    "created_at": ai_msg.created_at.isoformat() if ai_msg.created_at else "",
                    "reply_sticker": None,
                }

        # 2. 亲密度 + 完整 system prompt（人设/阶段/记忆/禁令，统一由 context_service 构建）
        friendship = await FriendshipDAO.get_by_user_soul(db, user_id, soul_id)
        intimacy = friendship.intimacy_level if friendship else 0
        full_system_prompt = await context_service.build_system_prompt(db, user_id, soul_id, intimacy, content)

        # 6. 对话历史（最近 N 轮）
        history = await ChatService.get_conversation_history(db, user_id, soul_id)

        # 7. 调用 LLM（BYOK：优先用户配置的 API Key）
        llm = await ChatService._make_llm(db, user_id)
        llm_ok = llm is not None
        if llm is None:
            ai_response = "（未配置 AI 服务：请在设置中配置 LLM API，或联系管理员开通权限）"
        else:
            try:
                # 经 HermesAgent 多轮工具调用（含 memory_tool：LLM 主动读写长期记忆）
                from core.agent import get_agent
                ai_response = await get_agent(user_id, soul_id).run(
                    llm,
                    system_prompt=full_system_prompt,
                    history=history,
                    user_message=content,
                )
                ai_response = clean_generated_text(ai_response)

            except Exception as e:
                from clients.llm_client import friendly_llm_error
                hint = friendly_llm_error(e, model=getattr(llm, "model", ""))
                ai_response = f"{_LLM_ERROR_PREFIX}{hint}）"
                logger.error(f"LLM 调用失败: {e}", extra={"user_id": str(user_id), "soul_id": soul_id}, exc_info=True)

        # 8. 存储 AI 回复（提取情绪 → TTS 情绪路由生效）
        from common.helpers import extract_emotion
        emotion = extract_emotion(ai_response)
        ai_msg = await MessageDAO.create(
            db,
            user_id=user_id,
            soul_id=soul_id,
            sender_type="ai",
            content=ai_response,
            emotion=emotion,
        )

        # 8.5 记忆由 agent 的 memory_tool 在对话中主动写入（不再走事后提取）

        # 8.6 AI 回表情包（STK）：用户发表情 → AI 用同情绪表情回应（sticker-for-sticker）
        reply_sticker = None
        if user_sticker:
            from services.sticker_service import StickerService
            reply_sticker = await StickerService.pick_by_emotion(db, user_sticker.emotion)
            if reply_sticker:
                await MessageDAO.update(db, ai_msg, sticker_id=reply_sticker.id)

        # 9. 更新 friendship：最后聊天时间 + 亲密度成长
        if friendship is not None:
            friendship.last_chat_at = datetime.now(timezone.utc).replace(tzinfo=None)
            if _is_meaningful(content) and ChatService._can_grow_today(user_id, soul_id):
                growth = ChatService._intimacy_growth(intimacy)
                friendship.intimacy_level = min(100, int(round(intimacy + growth)))
                ChatService._mark_grown_today(user_id, soul_id)

        # 10. 提交事务
        await db.commit()

        # 10.2 AI 延迟回复（人性化）：避免秒回，加入 1-3 秒的随机延迟
        import random
        delay = random.uniform(0.8, 2.5)  # 0.8-2.5 秒随机延迟
        await asyncio.sleep(delay)

        # 10.5 合成 AI 语音（CHAT-04/05）：非流式聊天需要把 voice_url 随响应返回给前端渲染语音条。
        voice_url = None
        if llm_ok and not ai_response.startswith(_LLM_ERROR_PREFIX) and ai_response != _FALLBACK_REPLY:
            voice_url = await ChatService._synthesize_tts_for_message(
                db, ai_msg, soul_id, ai_response, emotion, intimacy
            )

        # 11. 推送消息事件给用户（多端同步，RT-05）。推送独立于 db session，失败不影响主流程。
        # 有 voice_url 时：content 设为 null（不显示文字气泡），但返回 original_text（供用户右键转文字）
        try:
            from services.notify_service import push_message
            await push_message(
                user_id=str(user_id),
                message_data={
                    "user_message_id": user_msg.id,
                    "ai_message_id": ai_msg.id,
                    "content": None if voice_url else ai_response,
                    "original_text": ai_response if voice_url else None,
                    "emotion": ai_msg.emotion,
                    "created_at": ai_msg.created_at.isoformat(),
                    "sticker_url": reply_sticker.image_url if reply_sticker else None,
                    "voice_url": voice_url,
                },
            )
        except Exception as e:
            logger.warning(f"消息推送失败: {e}", exc_info=True)

        # API 响应：同样处理
        return {
            "user_message_id": user_msg.id,
            "ai_message_id": ai_msg.id,
            "content": None if voice_url else ai_response,
            "original_text": ai_response if voice_url else None,
            "emotion": ai_msg.emotion,
            "created_at": ai_msg.created_at.isoformat(),
            "voice_url": voice_url,
            "sticker_id": reply_sticker.id if reply_sticker else None,
            "sticker_name": reply_sticker.name if reply_sticker else None,
            "sticker_url": reply_sticker.image_url if reply_sticker else None,
            "sticker_emotion": reply_sticker.emotion if reply_sticker else None,
            "sticker_emoji": StickerService.fallback_emoji(reply_sticker) if reply_sticker else None,
        }

    # === 流式输出 ===
    @staticmethod
    async def prepare_stream(
            db: AsyncSession,
            user_id: uuid.UUID,
            soul_id: int,
            content: str,
    ):
        """
        流式聊天的前置准备：保存用户消息，返回上下文

        :return: (user_msg, system_prompt, history, friendship)
        """
        # 1. 保存用户消息
        user_msg = Message(
            user_id=user_id,
            soul_id=soul_id,
            sender_type="user",
            content=content,
        )
        db.add(user_msg)
        await db.flush()  # 获取 id
        await db.commit()  # ★ 必须提交：否则请求结束 get_db 会话关闭会回滚，后台任务将查不到用户消息

        # 2. 获取当前关系（亲密度）
        stmt = select(Friendship).where(
            Friendship.user_id == user_id,
            Friendship.soul_id == soul_id,
        )
        friendship = (await db.execute(stmt)).scalar_one_or_none()
        intimacy = friendship.intimacy_level if friendship else 0

        # 3. 拼接完整 System Prompt（人设/阶段/记忆/禁令，统一由 context_service 构建）
        full_system_prompt = await context_service.build_system_prompt(db, user_id, soul_id, intimacy, content)

        # 4. 获取对话历史
        history = await ChatService.get_conversation_history(db, user_id, soul_id)

        return user_msg, full_system_prompt, history, friendship

    @staticmethod
    async def save_ai_response(
            db: AsyncSession,
            user_id: uuid.UUID,
            soul_id: int,
            content: str,
            emotion: str = "neutral",
    ) -> Message:
        """
        保存 AI 回复（流式聊天完成后调用）
        """
        from common.helpers import extract_emotion
        if emotion == "neutral":
            emotion = extract_emotion(content)
        ai_msg = Message(
            user_id=user_id,
            soul_id=soul_id,
            sender_type="ai",
            content=content,
            emotion=emotion,
        )
        db.add(ai_msg)

        # 更新 friendship：最后聊天时间 + 亲密度成长（与非流式 send_message 保持一致）
        stmt = select(Friendship).where(
            Friendship.user_id == user_id,
            Friendship.soul_id == soul_id,
        )
        friendship = (await db.execute(stmt)).scalar_one_or_none()
        if friendship:
            friendship.last_chat_at = datetime.now(timezone.utc).replace(tzinfo=None)
            if _is_meaningful(content) and ChatService._can_grow_today(user_id, soul_id):
                intimacy = friendship.intimacy_level or 0
                growth = ChatService._intimacy_growth(intimacy)
                friendship.intimacy_level = min(100, int(round(intimacy + growth)))
                ChatService._mark_grown_today(user_id, soul_id)

        await db.commit()
        await db.refresh(ai_msg)
        return ai_msg

    # ---------------- 聊天历史（CHAT-06/07） ----------------
    @staticmethod
    async def get_history(
        db: AsyncSession,
        user_id: uuid.UUID,
        soul_id: int,
        offset: int = 0,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """分页获取聊天历史（按时间倒序取一页，再转正序返回）。"""
        from models.sticker import Sticker

        stmt = (
            select(Message, Sticker)
            .outerjoin(Sticker, Message.sticker_id == Sticker.id)
            .where(Message.user_id == user_id, Message.soul_id == soul_id)
            .order_by(desc(Message.id))
            .offset(offset)
            .limit(min(limit, 100))
        )
        rows = list((await db.execute(stmt)).all())
        rows.reverse()  # 转正序，与前端阅读方向一致
        return [
            {
                "message_id": m.id,
                "sender_type": m.sender_type,
                "content": m.content,
                "emotion": m.emotion,
                "msg_type": m.msg_type,
                "voice_url": m.voice_url,
                "original_text": m.content if m.voice_url else None,
                "sticker_id": sticker.id if sticker else None,
                "sticker_name": sticker.name if sticker else None,
                "sticker_url": sticker.image_url if sticker else None,
                "sticker_emotion": sticker.emotion if sticker else None,
                "sticker_emoji": StickerService.fallback_emoji(sticker) if sticker else None,
                "created_at": m.created_at.isoformat() if m.created_at else "",
                "is_recalled": m.is_recalled,
            }
            for m, sticker in rows
        ]

    @staticmethod
    async def clear_history(
        db: AsyncSession,
        user_id: uuid.UUID,
        soul_id: int,
    ) -> int:
        """清空某会话的聊天记录，返回删除条数。"""
        result = await db.execute(
            Message.__table__.delete().where(
                Message.user_id == user_id, Message.soul_id == soul_id
            )
        )
        await db.commit()
        return result.rowcount or 0

    # ==================== P1-01: 消息编辑 ====================
    @staticmethod
    async def edit_message(
        db: AsyncSession,
        message_id: int,
        new_content: str,
        user_id: uuid.UUID,
        time_window_minutes: int = 15,
    ) -> tuple[bool, str]:
        """编辑消息（需在发送后 15 分钟内）。

        Args:
            db: 数据库连接
            message_id: 消息 ID
            new_content: 新内容
            user_id: 编辑用户 ID（权限检查）
            time_window_minutes: 编辑时间窗口（分钟）

        Returns:
            (success, message) 元组
        """
        from datetime import datetime, timezone, timedelta

        msg = await MessageDAO.get(db, message_id)
        if not msg:
            return False, "消息不存在"

        # 权限检查
        if msg.user_id != user_id:
            return False, "只能编辑自己的消息"

        # 检查消息类型（只能编辑用户消息）
        if msg.sender_type != "user":
            return False, "不能编辑 AI 消息"

        # 时间窗口检查
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        elapsed = (now - msg.created_at).total_seconds() / 60
        if elapsed > time_window_minutes:
            return False, f"只能在消息发送后 {time_window_minutes} 分钟内编辑"

        # 执行编辑
        result = await MessageDAO.edit(db, message_id, new_content, user_id)
        if result:
            return True, "编辑成功"
        return False, "编辑失败"

    # ==================== P1-02: 消息转发 ====================
    @staticmethod
    async def forward_message(
        db: AsyncSession,
        message_id: int,
        target_user_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
    ) -> tuple[bool, str, Optional[int]]:
        """转发消息到指定站内好友。

        Args:
            db: 数据库连接
            message_id: 要转发的消息 ID
            target_user_id: 目标站内好友用户 ID
            user_id: 当前用户 ID（用于 rate limit 和权限检查）

        Returns:
            (success, message, new_message_id) 元组
        """
        # 源消息检查
        source_msg = await MessageDAO.get(db, message_id)
        if not source_msg:
            return False, "源消息不存在", None

        # 检查源消息是否已撤回
        if source_msg.is_recalled:
            return False, "不能转发已撤回的消息", None

        # 目标检查
        if not target_user_id:
            return False, "必须指定转发目标好友", None
        if not user_id:
            return False, "无法确认当前用户", None
        if target_user_id == user_id:
            return False, "不能转发给自己", None

        from services.friend_service import FriendService
        if not await FriendService._are_friends(db, user_id, target_user_id):
            return False, "只能转发给站内好友", None

        # 源消息必须属于当前用户可访问的 AI 会话或真人会话。
        if source_msg.conversation_id is not None:
            from dao.conversation_dao import ConversationDAO
            source_conv = await ConversationDAO.get(db, source_msg.conversation_id)
            if not source_conv or user_id not in (source_conv.user1_id, source_conv.user2_id):
                return False, "无权转发此消息", None
        elif source_msg.user_id != user_id:
            return False, "无权转发此消息", None

        # Rate limiting：每用户每分钟最多转发 10 次
        from services.emergency_handling_service import rate_limit_action
        if user_id:
            is_allowed = await rate_limit_action(
                db, str(user_id), "forward_message", max_count=10, time_window_seconds=60
            )
            if not is_allowed:
                return False, "转发过于频繁，请稍候再试", None

        # 转发逻辑
        try:
            from services.conversation_service import ConversationService
            conv = await ConversationService.get_or_create(db, user_id, target_user_id)
            new_msg = await MessageDAO.create(
                db,
                user_id=user_id,
                conversation_id=conv.id,
                soul_id=None,
                sender_type="user",
                content=source_msg.content,
                msg_type=source_msg.msg_type,
                sticker_id=source_msg.sticker_id,
                image_url=source_msg.image_url,
                voice_url=source_msg.voice_url,
                emotion=source_msg.emotion,
                forwarded_from_id=message_id,
            )
            from dao.conversation_dao import ConversationDAO
            await ConversationDAO.update(
                db,
                conv,
                last_message_id=new_msg.id,
                last_message_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            return True, "转发成功", new_msg.id
        except Exception as e:
            return False, f"转发失败: {str(e)}", None
