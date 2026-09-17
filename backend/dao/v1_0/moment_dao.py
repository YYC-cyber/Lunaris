# backend/dao/moment_dao.py
"""MomentDAO —— 朋友圈动态数据访问。"""
import uuid
from typing import List, Optional

from sqlalchemy import desc, select, update, delete, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from dao.base import BaseDAO
from models.v1_0.moment import Moment


class MomentDAO(BaseDAO[Moment]):
    model = Moment

    @classmethod
    async def list_timeline(cls, db: AsyncSession, limit: int = 20, offset: int = 0) -> List[Moment]:
        """获取全量时间线（不考虑隐私，仅保留用于兼容）"""
        stmt = (
            select(Moment)
            .where(Moment.is_deleted == False)  # noqa: E712  DB-03: 排除软删除
            .order_by(desc(Moment.created_at)).offset(offset).limit(limit)
        )
        return list((await db.execute(stmt)).scalars().all())

    @classmethod
    async def adjust_like(cls, db: AsyncSession, moment_id: int, delta: int) -> None:
        """like_count ±1。"""
        await db.execute(
            update(Moment)
            .where(Moment.id == moment_id)
            .values(like_count=Moment.like_count + delta)
        )

    @classmethod
    async def get_by_user(cls, db: AsyncSession, user_id: uuid.UUID) -> List[Moment]:
        """获取用户的所有朋友圈动态（用于数据导出）"""
        stmt = select(Moment).where(Moment.user_id == user_id)
        return list((await db.execute(stmt)).scalars().all())

    @classmethod
    async def delete_by_user(cls, db: AsyncSession, user_id: uuid.UUID) -> int:
        """删除用户的所有朋友圈动态（用于账户硬删除）"""
        result = await db.execute(
            delete(Moment).where(Moment.user_id == user_id)
        )
        return result.rowcount or 0

    @classmethod
    async def create_user_moment(
        cls, db: AsyncSession, *, user_id: uuid.UUID, content: str,
        images: Optional[List[str]] = None, visibility: str = "public",
        topic_tags: Optional[List[str]] = None,
        visible_groups: Optional[List[str]] = None,
        hidden_user_ids: Optional[List[str]] = None,
    ) -> Moment:
        """创建用户发布的动态"""
        return await cls.create(
            db,
            user_id=user_id,
            soul_id=None,
            content=content,
            images=images or [],
            topic_tags=topic_tags or [],
            visibility=visibility,
            visible_groups=visible_groups or [],
            hidden_user_ids=hidden_user_ids or [],
            is_ai_generated=False,
            like_count=0,
        )

    @classmethod
    async def get_owned(cls, db: AsyncSession, moment_id: int, user_id: uuid.UUID) -> Optional[Moment]:
        """获取指定用户拥有的动态（用于删除/权限校验）"""
        stmt = select(Moment).where(
            Moment.id == moment_id,
            Moment.user_id == user_id
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    @classmethod
    async def list_timeline_visible(
        cls, db: AsyncSession, *, viewer_id: uuid.UUID, friend_ids: Optional[List[uuid.UUID]] = None,
        limit: int = 20, offset: int = 0,
    ) -> List[Moment]:
        """
        时间线查询（考虑隐私规则）：
        - AI 动态（soul_id != NULL）：对所有人可见
        - 用户动态（user_id != NULL）：
          * public: 所有人可见
          * private: 仅作者可见
          * friends: 仅作者和好友可见
          * visible_groups: 如非空，则需在该列表中至少一个分组内
          * hidden_user_ids: 如包含 viewer_id，则不可见
        """
        friend_ids = friend_ids or []

        # AI 动态（始终可见）
        ai_moments = select(Moment).where(
            Moment.soul_id.isnot(None),
            Moment.is_deleted == False,  # noqa: E712  DB-03: 排除软删除
        )

        # 用户动态（按隐私规则）
        user_moments = select(Moment).where(
            Moment.user_id.isnot(None),
            Moment.is_deleted == False,  # noqa: E712  DB-03: 排除软删除
            or_(
                Moment.visibility == "public",
                Moment.user_id == viewer_id,  # 作者自己总能看到
                and_(
                    Moment.visibility == "friends",
                    Moment.user_id.in_(friend_ids) if friend_ids else False,
                )
            )
        )

        # 合并、排序、分页
        from sqlalchemy import union_all
        stmt = (
            union_all(ai_moments, user_moments)
            .order_by(desc(Moment.created_at))
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(stmt)
        moments = list(result.scalars().all())

        # 过滤：检查 visible_groups 和 hidden_user_ids
        filtered = []
        viewer_id_str = str(viewer_id)
        for m in moments:
            # 检查 hidden_user_ids：如果当前用户在隐藏列表，不返回（除非是作者自己）
            if m.hidden_user_ids and isinstance(m.hidden_user_ids, list):
                if viewer_id_str in [str(uid) for uid in m.hidden_user_ids] and m.user_id != viewer_id:
                    continue

            # 检查 visible_groups：如非空，需要检查分组权限
            if m.visible_groups and isinstance(m.visible_groups, list) and len(m.visible_groups) > 0:
                # 仅当用户在指定分组内时才可见（目前使用硬编码分组，实际生产需 UserGroup 表）
                # 对于 MVP，我们允许：作者自己、hardcoded group members（需扩展）
                if m.user_id != viewer_id:
                    # TODO: 实现分组成员检查 (需要 UserGroup 表)
                    # 为 MVP 起见，暂时：如设置了 visible_groups，仅作者可见
                    continue

            filtered.append(m)

        return filtered


