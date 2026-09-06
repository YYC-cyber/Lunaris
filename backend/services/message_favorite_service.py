"""消息收藏服务层"""
import uuid
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from dao.message_favorite_dao import MessageFavoriteDAO
from dao.message_dao import MessageDAO


class MessageFavoriteService:
    """消息收藏服务"""

    @staticmethod
    async def add(db: AsyncSession, user_id: uuid.UUID, message_id: int, category: str = '默认') -> Optional[dict]:
        """添加消息到收藏夹。

        Args:
            db: 数据库连接
            user_id: 用户 ID
            message_id: 消息 ID
            category: 收藏分类

        Returns:
            收藏记录字典，或 None 如果已收藏
        """
        # 检查消息是否存在
        msg = await MessageDAO.get(db, message_id)
        if not msg:
            return None

        favorite = await MessageFavoriteDAO.add(db, user_id, message_id, category)
        if not favorite:
            return None

        return {
            "id": favorite.id,
            "user_id": str(favorite.user_id),
            "message_id": favorite.message_id,
            "category": favorite.category,
            "created_at": favorite.created_at.isoformat() if favorite.created_at else None,
        }

    @staticmethod
    async def remove(db: AsyncSession, user_id: uuid.UUID, message_id: int) -> bool:
        """从收藏夹移除消息。

        Args:
            db: 数据库连接
            user_id: 用户 ID
            message_id: 消息 ID

        Returns:
            是否成功移除
        """
        return await MessageFavoriteDAO.remove(db, user_id, message_id)

    @staticmethod
    async def list(
        db: AsyncSession,
        user_id: uuid.UUID,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """获取用户的收藏消息列表（分页）。

        Args:
            db: 数据库连接
            user_id: 用户 ID
            category: 收藏分类（None 表示全部）
            limit: 限制条数
            offset: 偏移

        Returns:
            包含 items、total、offset 的字典
        """
        items = await MessageFavoriteDAO.list_by_user(db, user_id, category, limit, offset)
        total = await MessageFavoriteDAO.count_by_user(db, user_id, category)
        return {
            "items": items,
            "total": total,
            "offset": offset,
            "count": len(items),
        }

    @staticmethod
    async def search(
        db: AsyncSession,
        user_id: uuid.UUID,
        keyword: str,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """按关键词搜索用户收藏的消息。

        Args:
            db: 数据库连接
            user_id: 用户 ID
            keyword: 搜索关键词
            limit: 限制条数
            offset: 偏移

        Returns:
            包含 items、offset 的字典
        """
        items = await MessageFavoriteDAO.search_by_user(db, user_id, keyword, limit, offset)
        return {
            "items": items,
            "offset": offset,
            "count": len(items),
            "keyword": keyword,
        }
