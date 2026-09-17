# backend/services/conversation_service.py
"""会话服务（FRI-06）—— 真人好友之间的一对一聊天（数据访问走 DAO 层）。

【统一消息表】真人消息和 AI 消息共用 `messages` 表：
- AI 消息：conversation_id 为空，soul_id 指向角色
- 真人消息：conversation_id 指向会话，soul_id 为空
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from dao.v1_0.conversation_dao import ConversationDAO
from dao.v1_0.message_dao import MessageDAO
from dao.user_dao import UserDAO
from models.v1_0.conversation import Conversation
from services.v1_0.friend_service import FriendService


class ConversationService:
    @staticmethod
    async def get_or_create(db: AsyncSession, user_a: uuid.UUID, user_b: uuid.UUID) -> Conversation:
        """查找或创建两人之间的唯一会话。"""
        conv = await ConversationDAO.get_by_pair(db, user_a, user_b)
        if conv:
            return conv
        conv = await ConversationDAO.create(
            db,
            user1_id=user_a,
            user2_id=user_b,
        )
        return conv

    @staticmethod
    async def send_message(
        db: AsyncSession,
        sender_id: uuid.UUID,
        receiver_id: uuid.UUID,
        content: str,
        msg_type: str = "text",
        sticker_id: int | None = None,
        image_url: str | None = None,
        voice_url: str | None = None,
    ):
        """发送真人消息（需互为好友），存入统一 messages 表并更新会话。

        支持表情包（msg_type='sticker'，sticker_id 指定）和图片（msg_type='image'，image_url 指定）。
        """
        if sender_id == receiver_id:
            raise ValueError("不能给自己发消息")
        if not await FriendService._are_friends(db, sender_id, receiver_id):
            raise ValueError("你们不是好友，无法发消息")

        from services.sticker_service import StickerService
        sticker = await StickerService.get(db, sticker_id) if sticker_id else None

        conv = await ConversationService.get_or_create(db, sender_id, receiver_id)

        # 判断实际的消息类型
        actual_msg_type = msg_type
        actual_content = content
        if sticker:
            actual_msg_type = "sticker"
            actual_content = sticker.name
        elif msg_type == "image":
            actual_msg_type = "image"
            actual_content = content or "（分享了一张图片）"
        elif msg_type == "voice":
            actual_msg_type = "voice"
            actual_content = content or "（语音消息）"

        msg = await MessageDAO.create(
            db,
            conversation_id=conv.id,
            user_id=sender_id,
            soul_id=None,          # 真人消息不指向角色
            sender_type="user",
            content=actual_content,
            msg_type=actual_msg_type,
            sticker_id=sticker_id,
            image_url=image_url,
            voice_url=voice_url,
        )
        # 更新会话最后消息（列表排序/预览）
        await ConversationDAO.update(
            db, conv,
            last_message_id=msg.id,
            last_message_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        return msg

    @staticmethod
    async def list_conversations(db: AsyncSession, user_id: uuid.UUID) -> List[Dict[str, Any]]:
        """我的会话列表（按最后消息时间倒序），含对方信息与最后一条消息预览。"""
        convs = await ConversationDAO.list_by_user(db, user_id)
        result = []
        for conv in convs:
            other_id = conv.user2_id if conv.user1_id == user_id else conv.user1_id
            other = await UserDAO.get(db, other_id)
            last_msg = await MessageDAO.get(db, conv.last_message_id) if conv.last_message_id else None
            result.append({
                "conversation_id": conv.id,
                "other_user": {
                    "user_id": str(other.id),
                    "lunaris_id": other.lunaris_id,
                    "nickname": other.nickname or other.username,
                    "avatar_url": other.avatar_url,
                } if other else None,
                "last_message": last_msg.content if last_msg else None,
                "last_message_at": conv.last_message_at.isoformat() if conv.last_message_at else None,
            })
        return result

    @staticmethod
    async def list_messages(
        db: AsyncSession,
        user_id: uuid.UUID,
        conversation_id: int,
        offset: int = 0,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """某会话的消息历史（校验参与者身份）。"""
        conv = await ConversationDAO.get(db, conversation_id)
        if not conv:
            raise ValueError("会话不存在")
        if user_id not in (conv.user1_id, conv.user2_id):
            raise ValueError("不是该会话参与者")

        msgs = await MessageDAO.list_by_conversation(db, conversation_id, offset, limit)
        msgs.reverse()  # 转正序
        return [
            {
                "message_id": m.id,
                "sender_id": str(m.user_id),
                "content": m.content,
                "msg_type": m.msg_type,
                "image_url": m.image_url if m.msg_type == "image" else None,
                "voice_url": m.voice_url if m.msg_type == "voice" else None,
                "created_at": m.created_at.isoformat() if m.created_at else "",
            }
            for m in msgs
        ]
