"""
SoulService —— 角色/好友业务（数据访问走 DAO 层）。

【职责】
- get_paired_souls / get_available_souls：角色列表
- send_first_greeting：配对后 AI 开场白（SOUL-05）
- add_soul / set_primary / remove_soul：好友管理
"""
import uuid
from typing import Dict, List, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from common.helpers import opposite_gender
from dao.v1_0.friendship_dao import FriendshipDAO
from dao.v1_0.message_dao import MessageDAO
from dao.v1_0.soul_dao import SoulDAO
from models.v1_0.friendship import Friendship
from models.v1_0.soul import Soul


class SoulService:
    @staticmethod
    async def get_paired_souls(db: AsyncSession, user_id: uuid.UUID) -> List[Soul]:
        """获取当前用户已配对的角色列表。"""
        return await SoulDAO.list_paired(db, user_id)

    @staticmethod
    async def get_paired_soul_items(db: AsyncSession, user_id: uuid.UUID) -> List[Dict]:
        """获取已配对角色，并用 friendship.is_primary 标记当前默认伴侣。"""
        souls = await SoulDAO.list_paired(db, user_id)
        friendships = await FriendshipDAO.list_by_user(db, user_id)
        primary_by_soul_id = {
            friendship.soul_id: bool(friendship.is_primary)
            for friendship in friendships
        }

        return [
            {
                "id": soul.id,
                "name": soul.name,
                "display_name": soul.display_name,
                "gender": soul.gender,
                "first_greeting": soul.first_greeting,
                "avatar_url": soul.avatar_url,
                "voice_id": soul.voice_id,
                "tags": soul.tags,
                "is_default": primary_by_soul_id.get(soul.id, False),
                "sort_order": soul.sort_order,
            }
            for soul in souls
        ]

    @staticmethod
    async def get_available_souls(
        db: AsyncSession, user_id: uuid.UUID, user_gender: Literal["male", "female"]
    ) -> List[Soul]:
        """可添加的异性角色（排除已配对）。"""
        target_gender = opposite_gender(user_gender)
        return await SoulDAO.list_available(db, user_id, target_gender)

    # ---------- 好友管理 ----------
    @staticmethod
    async def send_first_greeting(db: AsyncSession, user_id: uuid.UUID, soul_id: int) -> None:
        """配对成功后，AI 主动发送开场白（SOUL-05），并推送。"""
        soul = await SoulDAO.get(db, soul_id)
        if not soul or not soul.first_greeting:
            return

        msg = await MessageDAO.create(
            db,
            user_id=user_id,
            soul_id=soul_id,
            sender_type="ai",
            content=soul.first_greeting,
        )

        # 推送开场白（多端同步）
        try:
            from services.notify_service import push_message
            await push_message(
                user_id=str(user_id),
                message_data={
                    "user_message_id": None,
                    "ai_message_id": msg.id,
                    "content": msg.content,
                    "emotion": "neutral",
                    "created_at": msg.created_at.isoformat() if msg.created_at else "",
                },
            )
        except Exception as e:
            print(f"⚠️ 开场白推送失败: {e}")

    @staticmethod
    async def add_soul(
        db: AsyncSession, user_id: uuid.UUID, user_gender: str, soul_id: int
    ) -> Friendship:
        """添加角色为好友（SOUL-03）：校验异性 + 去重，创建 friendship 并发送开场白。"""
        soul = await SoulDAO.get(db, soul_id)
        if not soul:
            raise ValueError("角色不存在")
        if soul.gender == user_gender:
            raise ValueError("只能添加异性角色为好友")
        exists = await FriendshipDAO.get_by_user_soul(db, user_id, soul_id)
        if exists:
            raise ValueError("该角色已在你的好友列表")

        friendship = await FriendshipDAO.create(
            db, user_id=user_id, soul_id=soul_id, intimacy_level=0, is_primary=False
        )
        # AI 开场白
        await SoulService.send_first_greeting(db, user_id, soul_id)
        return friendship

    @staticmethod
    async def set_primary(db: AsyncSession, user_id: uuid.UUID, soul_id: int) -> None:
        """设为默认伴侣（SOUL-04）：同一用户同时只有一个默认伴侣。"""
        exists = await FriendshipDAO.get_by_user_soul(db, user_id, soul_id)
        if not exists:
            raise ValueError("好友关系不存在")

        # 先清空该用户所有默认标记，再设置目标
        await FriendshipDAO.clear_primary(db, user_id)
        await FriendshipDAO.update(db, exists, is_primary=True)

    @staticmethod
    async def remove_soul(db: AsyncSession, user_id: uuid.UUID, soul_id: int) -> None:
        """删除好友（按产品决策：只删好友关系，保留聊天记录）。"""
        friendship = await FriendshipDAO.get_by_user_soul(db, user_id, soul_id)
        if not friendship:
            raise ValueError("好友关系不存在")
        await FriendshipDAO.delete(db, friendship)
