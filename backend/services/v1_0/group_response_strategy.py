"""群聊 AI 回应策略"""
import random
import re
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from dao.v1_0.group_chat_dao import GroupMessageDAO
from dao.v1_0.soul_dao import SoulDAO
from dao.v1_0.friendship_dao import FriendshipDAO
import uuid


class GroupResponseStrategy:
    """AI 在群聊中的回应策略"""

    # 追踪 AI 最后说过话的时间
    _ai_last_spoke = {}  # {(soul_id, group_id): datetime}

    @staticmethod
    async def should_respond(
        db: AsyncSession,
        ai_soul_id: int,
        group_id: int,
        last_message_content: str,
        last_message_sender: str,  # 'ai' 或 'user'
        user_id: uuid.UUID,
        group_type: str,  # 'ai_only' / 'human_only' / 'mixed'
        intimacy: int,  # 0-100 亲密度
        mentioned_user_ids: Optional[list[str]] = None,
        force_respond: bool = False,
    ) -> bool:
        """
        判断 AI 是否应该在群聊中回应

        score 系统（满分 100）：
        - score > 60：应该回应
        - score <= 60：保持沉默
        """

        score = 0

        # 【规则 1】如果是"人类专属"群，AI 完全不回应
        if group_type == "human_only":
            return False

        if force_respond:
            return True

        # 【规则 2】被 @ 了？优先度最高
        soul = await SoulDAO.get(db, ai_soul_id)
        mentioned_ids = {str(value).strip() for value in (mentioned_user_ids or []) if value}
        mentioned_names = {
            match.group(1).strip().lower()
            for match in re.finditer(r"@([^\s@]+)", last_message_content or "")
        }
        is_mentioned = str(ai_soul_id) in mentioned_ids
        if soul and (
            is_mentioned
            or str(soul.display_name or "").strip().lower() in mentioned_names
            or str(soul.name or "").strip().lower() in mentioned_names
        ):
            return True  # 直接返回，无条件回应

        # 【规则 3】被直接问问题？
        if GroupResponseStrategy._is_direct_question(last_message_content, soul.display_name if soul else ""):
            return True

        # 【规则 4】群聊类型影响主动性
        if group_type == "ai_only":
            score += 70  # AI 多人聊天，积极参与
        elif group_type == "mixed":
            score += 20  # 混合聊天，保持低调（@才主动回应）

        # 【规则 5】发言者是谁？
        if last_message_sender == "user":
            score += 50  # 用户发言，更应该回应
        elif last_message_sender == "ai":
            score += 20  # 其他 AI 发言，适度参与

        # 【规则 6】AI 最近说过话吗？不要连续说
        key = (ai_soul_id, group_id)
        last_spoke_time = GroupResponseStrategy._ai_last_spoke.get(key)
        if last_spoke_time:
            seconds_since = (datetime.now() - last_spoke_time).total_seconds()
            if seconds_since < 10:
                score -= 80  # 刚说完，大幅降低概率

        # 【规则 7】话题是不是 AI 擅长的？
        topic_relevance = GroupResponseStrategy._calculate_topic_relevance(
            last_message_content,
            soul.name if soul else ""
        )
        score += topic_relevance * 30  # 0-30 分

        # 【规则 8】对话热度：不要太多人同时回应
        recent_responders = await GroupResponseStrategy._count_recent_responders(
            db,
            group_id,
            seconds=5
        )
        if recent_responders > 2:
            score -= 50  # 已经很热闹了，退缩一下

        # 【规则 9】亲密度影响：越亲密越主动
        score += (intimacy / 100) * 40  # 0-40 分

        # 最后用概率决定
        threshold = 60
        return score > threshold

    @staticmethod
    def _is_direct_question(content: str, ai_name: str) -> bool:
        """检查是否是对这个 AI 的直接问题"""
        question_indicators = ["吗？", "呢？", "怎么", "什么", "为什么", "如何", "能不能", "可以吗"]
        has_question = any(q in content for q in question_indicators)
        return has_question and len(content) < 100  # 短消息且有疑问词

    @staticmethod
    def _calculate_topic_relevance(content: str, ai_name: str) -> float:
        """计算话题与 AI 的相关性（0-1）"""
        # 这里简化处理，实际可以用 NLP 或关键词匹配
        # Diana - 音乐、钢琴
        # Kael - 日常、开心
        # Caelus - 诗意、哲学
        # 等等

        if ai_name.lower() == "diana":
            diana_keywords = ["音乐", "钢琴", "古典", "肖邦", "演出", "曲子"]
            return 1.0 if any(k in content for k in diana_keywords) else 0.3
        elif ai_name.lower() == "kael":
            kael_keywords = ["开心", "有趣", "活动", "朋友", "玩"]
            return 1.0 if any(k in content for k in kael_keywords) else 0.4
        elif ai_name.lower() == "caelus":
            caelus_keywords = ["诗", "哲学", "思考", "意义", "人生"]
            return 1.0 if any(k in content for k in caelus_keywords) else 0.3

        return 0.5  # 默认中等相关性

    @staticmethod
    async def _count_recent_responders(
        db: AsyncSession,
        group_id: int,
        seconds: int = 5
    ) -> int:
        """统计最近 N 秒内有多少个不同的发言者"""
        cutoff_time = datetime.now() - timedelta(seconds=seconds)
        messages = await GroupMessageDAO.list_messages(db, group_id, limit=20)

        responders = set()
        for msg in messages:
            if msg.created_at > cutoff_time:
                if msg.sender_type == "ai":
                    responders.add(f"ai_{msg.soul_id}")
                else:
                    responders.add(f"user_{msg.sender_id}")

        return len(responders)

    @staticmethod
    def mark_ai_spoke(ai_soul_id: int, group_id: int) -> None:
        """记录 AI 在群聊中说过话的时间"""
        key = (ai_soul_id, group_id)
        GroupResponseStrategy._ai_last_spoke[key] = datetime.now()
