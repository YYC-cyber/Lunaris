# backend/services/search_service.py
"""搜索服务 —— 消息搜索。"""
from datetime import datetime
from typing import List, Optional, Tuple
import uuid

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from dao.base import BaseDAO
from models.message import Message
from models.user import User


class SearchService:
    @staticmethod
    async def search_messages(
        db: AsyncSession,
        current_user_id: uuid.UUID,
        keyword: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        sender_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Message], int]:
        """搜索当前用户的消息。

        搜索当前用户所在的对话（真人聊天）中包含关键词的消息。
        支持按发件人、日期范围过滤。

        Returns:
            (messages, total_count)
        """
        # 构建搜索条件
        filters = [
            # 关键词搜索（ILIKE 大小写不敏感）
            Message.content.ilike(f"%{keyword}%"),
        ]

        # 日期范围过滤
        if from_date:
            filters.append(Message.created_at >= from_date)
        if to_date:
            filters.append(Message.created_at <= to_date)

        # 发件人过滤
        if sender_id:
            filters.append(Message.user_id == sender_id)

        # 会话过滤：只查询当前用户参与的对话中的消息
        # 通过 conversation_id 关联 conversations 表，检查 current_user 是否参与
        from models.conversation import Conversation

        stmt = (
            select(Message)
            .join(
                Conversation,
                Message.conversation_id == Conversation.id,
                isouter=False,
            )
            .where(
                and_(
                    or_(
                        Conversation.user1_id == current_user_id,
                        Conversation.user2_id == current_user_id,
                    ),
                    *filters,
                )
            )
            .order_by(Message.created_at.desc())
        )

        # 查询总数
        count_stmt = select(func.count()).select_from(stmt.alias())
        total = (await db.execute(count_stmt)).scalar_one()

        # 分页查询
        messages = list(
            (await db.execute(stmt.offset(offset).limit(limit))).scalars().all()
        )

        # 补充发件人信息
        # 从查询结果中获取所有 user_id，然后批量查询 User
        user_ids = {msg.user_id for msg in messages}
        users_map = {}
        if user_ids:
            users = (
                await db.execute(select(User).where(User.id.in_(user_ids)))
            ).scalars().all()
            users_map = {user.id: user for user in users}

        # 将发件人信息附加到 Message 对象上（动态属性）
        for msg in messages:
            msg._sender = users_map.get(msg.user_id)

        return messages, total
