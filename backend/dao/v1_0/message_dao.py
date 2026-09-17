# backend/dao/message_dao.py
"""MessageDAO —— 统一消息表数据访问（AI + 真人消息）。"""
import uuid
from typing import List, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from dao.base import BaseDAO
from models.v1_0.message import Message


class MessageDAO(BaseDAO[Message]):
    model = Message

    @classmethod
    async def list_by_soul(
        cls, db: AsyncSession, user_id: uuid.UUID, soul_id: int, limit: int = 20
    ) -> List[Message]:
        """某用户与某 AI 角色最近 N 条（按时间倒序）。"""
        stmt = (
            select(Message)
            .where(
                Message.user_id == user_id,
                Message.soul_id == soul_id,
                Message.is_deleted == False,  # noqa: E712  DB-03
            )
            .order_by(desc(Message.id))
            .limit(limit)
        )
        return list((await db.execute(stmt)).scalars().all())

    @classmethod
    async def list_by_conversation(
        cls, db: AsyncSession, conversation_id: int, offset: int = 0, limit: int = 50
    ) -> List[Message]:
        """某真人会话的消息（分页，倒序取一页）。"""
        stmt = (
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.is_deleted == False,  # noqa: E712  DB-03
            )
            .order_by(desc(Message.id))
            .offset(offset)
            .limit(limit)
        )
        return list((await db.execute(stmt)).scalars().all())

    @classmethod
    async def clear_by_soul(cls, db: AsyncSession, user_id: uuid.UUID, soul_id: int) -> int:
        """清空某用户与某 AI 的聊天记录。"""
        from sqlalchemy import delete
        result = await db.execute(
            delete(Message).where(
                Message.user_id == user_id, Message.soul_id == soul_id
            )
        )
        return result.rowcount or 0

    @classmethod
    async def get(cls, db: AsyncSession, obj_id: int) -> Optional[Message]:
        return (
            await db.execute(select(Message).where(Message.id == obj_id))
        ).scalar_one_or_none()

    @classmethod
    async def recall(cls, db: AsyncSession, message_id: int) -> bool:
        """撤回消息（仅标记为已撤回，不真正删除）。"""
        msg = await cls.get(db, message_id)
        if not msg:
            return False
        msg.is_recalled = True
        await db.commit()
        return True

    @classmethod
    async def get_by_user(cls, db: AsyncSession, user_id: uuid.UUID) -> List[Message]:
        """获取用户的所有消息（用于数据导出）"""
        stmt = select(Message).where(Message.user_id == user_id)
        return list((await db.execute(stmt)).scalars().all())

    @classmethod
    async def delete_by_user(cls, db: AsyncSession, user_id: uuid.UUID) -> int:
        """删除用户的所有消息（用于账户硬删除）"""
        from sqlalchemy import delete
        result = await db.execute(
            delete(Message).where(Message.user_id == user_id)
        )
        return result.rowcount or 0

    @classmethod
    async def list_recent_stickers(
        cls, db: AsyncSession, user_id: uuid.UUID, limit: int = 20
    ) -> List[dict]:
        """获取用户最近使用过的表情包列表（按最后一次使用时间倒序）。"""
        from sqlalchemy import func
        from models.sticker import Sticker
        from services.sticker_service import StickerService

        stmt = (
            select(
                Sticker.id,
                Sticker.name,
                Sticker.emotion,
                Sticker.image_url,
                Sticker.category,
                func.max(Message.created_at).label("last_used"),
            )
            .join(Message, Message.sticker_id == Sticker.id)
            .where(Message.user_id == user_id, Message.sticker_id.isnot(None))
            .group_by(Sticker.id)
            .order_by(desc(func.max(Message.created_at)))
            .limit(limit)
        )
        results = (await db.execute(stmt)).all()

        return [
            {
                "id": row[0],
                "name": row[1],
                "emotion": row[2],
                "image_url": row[3],
                "category": row[4],
                "sticker_emoji": StickerService.fallback_emoji_simple(row[1], row[3]),
            }
            for row in results
        ]

    @classmethod
    async def edit(cls, db: AsyncSession, message_id: int, new_content: str, user_id: uuid.UUID) -> Optional[dict]:
        """编辑消息：检查权限、记录编辑历史、更新内容和编辑时间戳。

        Args:
            db: 数据库连接
            message_id: 消息 ID
            new_content: 新内容
            user_id: 编辑用户 ID（用于权限检查）

        Returns:
            编辑后的消息字典，或 None 如果消息不存在或用户无权限
        """
        from datetime import datetime, timezone
        from models.message_edit_history import MessageEditHistory

        msg = await cls.get(db, message_id)
        if not msg:
            return None

        # 权限检查：只有消息发送者可以编辑
        if msg.user_id != user_id:
            return None

        # 记录编辑历史
        edit_history = MessageEditHistory(
            message_id=message_id,
            old_content=msg.content,
            edited_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(edit_history)

        # 更新消息
        msg.content = new_content
        msg.is_edited = True
        msg.edited_at = datetime.now(timezone.utc).replace(tzinfo=None)

        await db.commit()
        await db.refresh(msg)

        return {
            "id": msg.id,
            "content": msg.content,
            "is_edited": msg.is_edited,
            "edited_at": msg.edited_at.isoformat() if msg.edited_at else None,
        }
