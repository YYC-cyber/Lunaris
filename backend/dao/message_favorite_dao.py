"""MessageFavoriteDAO —— 消息收藏数据访问层。"""
import uuid
from typing import List, Optional

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.message_favorite import MessageFavorite
from models.message import Message


class MessageFavoriteDAO:
    """消息收藏数据访问对象"""

    @staticmethod
    async def add(db: AsyncSession, user_id: uuid.UUID, message_id: int, category: str = '默认') -> Optional[MessageFavorite]:
        """添加消息到收藏夹。

        Args:
            db: 数据库连接
            user_id: 用户 ID
            message_id: 消息 ID
            category: 收藏分类，默认 '默认'

        Returns:
            创建的 MessageFavorite 记录，或 None 如果已存在
        """
        # 检查是否已收藏
        stmt = select(MessageFavorite).where(
            and_(MessageFavorite.user_id == user_id, MessageFavorite.message_id == message_id)
        )
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            return None

        favorite = MessageFavorite(
            user_id=user_id,
            message_id=message_id,
            category=category,
        )
        db.add(favorite)
        await db.commit()
        await db.refresh(favorite)
        return favorite

    @staticmethod
    async def remove(db: AsyncSession, user_id: uuid.UUID, message_id: int) -> bool:
        """从收藏夹移除消息。

        Args:
            db: 数据库连接
            user_id: 用户 ID
            message_id: 消息 ID

        Returns:
            是否成功移除（True 如果记录存在且已删除，False 如果记录不存在）
        """
        stmt = select(MessageFavorite).where(
            and_(MessageFavorite.user_id == user_id, MessageFavorite.message_id == message_id)
        )
        favorite = (await db.execute(stmt)).scalar_one_or_none()
        if not favorite:
            return False

        await db.delete(favorite)
        await db.commit()
        return True

    @staticmethod
    async def list_by_user(
        db: AsyncSession,
        user_id: uuid.UUID,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[dict]:
        """获取用户的收藏消息列表（分页）。

        Args:
            db: 数据库连接
            user_id: 用户 ID
            category: 收藏分类（None 表示全部）
            limit: 限制条数
            offset: 偏移

        Returns:
            消息收藏列表，包含消息内容和收藏信息
        """
        stmt = (
            select(MessageFavorite, Message)
            .join(Message, MessageFavorite.message_id == Message.id)
            .where(MessageFavorite.user_id == user_id)
        )

        if category:
            stmt = stmt.where(MessageFavorite.category == category)

        stmt = stmt.order_by(desc(MessageFavorite.created_at)).offset(offset).limit(limit)

        rows = list((await db.execute(stmt)).all())
        return [
            {
                "favorite_id": fav.id,
                "message_id": msg.id,
                "content": msg.content,
                "category": fav.category,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
                "message_created_at": msg.created_at.isoformat() if msg.created_at else None,
                "is_edited": msg.is_edited,
                "edited_at": msg.edited_at.isoformat() if msg.edited_at else None,
            }
            for fav, msg in rows
        ]

    @staticmethod
    async def search_by_user(
        db: AsyncSession,
        user_id: uuid.UUID,
        keyword: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[dict]:
        """按关键词搜索用户收藏的消息。

        Args:
            db: 数据库连接
            user_id: 用户 ID
            keyword: 搜索关键词
            limit: 限制条数
            offset: 偏移

        Returns:
            匹配的消息列表
        """
        from sqlalchemy import func, or_

        # 使用 ILIKE 进行不区分大小写的模糊搜索
        stmt = (
            select(MessageFavorite, Message)
            .join(Message, MessageFavorite.message_id == Message.id)
            .where(
                and_(
                    MessageFavorite.user_id == user_id,
                    Message.content.ilike(f"%{keyword}%")
                )
            )
            .order_by(desc(MessageFavorite.created_at))
            .offset(offset)
            .limit(limit)
        )

        rows = list((await db.execute(stmt)).all())
        return [
            {
                "favorite_id": fav.id,
                "message_id": msg.id,
                "content": msg.content,
                "category": fav.category,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
                "message_created_at": msg.created_at.isoformat() if msg.created_at else None,
                "is_edited": msg.is_edited,
                "edited_at": msg.edited_at.isoformat() if msg.edited_at else None,
            }
            for fav, msg in rows
        ]

    @staticmethod
    async def get(db: AsyncSession, favorite_id: int) -> Optional[MessageFavorite]:
        """按 ID 获取收藏记录。"""
        stmt = select(MessageFavorite).where(MessageFavorite.id == favorite_id)
        return (await db.execute(stmt)).scalar_one_or_none()

    @staticmethod
    async def count_by_user(db: AsyncSession, user_id: uuid.UUID, category: Optional[str] = None) -> int:
        """统计用户收藏数量。"""
        from sqlalchemy import func

        stmt = select(func.count()).select_from(MessageFavorite).where(MessageFavorite.user_id == user_id)
        if category:
            stmt = stmt.where(MessageFavorite.category == category)
        return (await db.execute(stmt)).scalar_one() or 0
