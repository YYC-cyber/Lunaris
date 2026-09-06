# backend/dao/base.py
"""通用 DAO 基类 —— 提供 CRUD 和查询操作。

【用法】子类设置 model：
    class UserDAO(BaseDAO[User]):
        model = User

【约定】
- 事务边界由 service 层控制；DAO 方法内部 commit（简单场景）
- 复杂事务可在 service 层用 db.begin() 包裹
- 子类应继承通用方法，仅实现 domain-specific 查询（如 list_active, search_by_keyword）

【常见模式】
- 分页列表: await MyDAO.list(db, offset=0, limit=50)
- 计数: await MyDAO.count(db, status='active')
- 条件查询: 子类实现 get_by_field() 方法
"""
from typing import Any, Generic, Optional, TypeVar, List

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class BaseDAO(Generic[T]):
    model = None

    @classmethod
    async def get(cls, db: AsyncSession, obj_id: Any) -> Optional[T]:
        """按主键查询。"""
        return (
            await db.execute(select(cls.model).where(cls.model.id == obj_id))
        ).scalar_one_or_none()

    @classmethod
    async def list(
        cls,
        db: AsyncSession,
        *,
        offset: int = 0,
        limit: int = 50,
        order_by=None,
    ) -> List[T]:
        """分页列表查询。"""
        stmt = select(cls.model)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        stmt = stmt.offset(offset).limit(limit)
        return list((await db.execute(stmt)).scalars().all())

    @classmethod
    async def list_all(cls, db: AsyncSession, order_by=None) -> List[T]:
        """获取所有记录（不分页）。"""
        stmt = select(cls.model)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        return list((await db.execute(stmt)).scalars().all())

    @classmethod
    async def create(cls, db: AsyncSession, **fields) -> T:
        """创建记录（自动 commit + refresh）。"""
        obj = cls.model(**fields)
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        return obj

    @classmethod
    async def update(cls, db: AsyncSession, obj: T, **fields) -> T:
        """更新记录字段（自动 commit + refresh）。"""
        for k, v in fields.items():
            setattr(obj, k, v)
        await db.commit()
        await db.refresh(obj)
        return obj

    @classmethod
    async def delete(cls, db: AsyncSession, obj: T) -> None:
        """删除记录（自动 commit）。"""
        await db.delete(obj)
        await db.commit()

    @classmethod
    async def count(cls, db: AsyncSession, **filters) -> int:
        """按等值条件计数。过滤参数作为 AND 条件。"""
        stmt = select(func.count()).select_from(cls.model)
        for k, v in filters.items():
            stmt = stmt.where(getattr(cls.model, k) == v)
        return (await db.execute(stmt)).scalar_one()

    @classmethod
    async def count_all(cls, db: AsyncSession) -> int:
        """获取表中所有记录数。"""
        stmt = select(func.count()).select_from(cls.model)
        return (await db.execute(stmt)).scalar_one()

    @classmethod
    async def exists(cls, db: AsyncSession, **filters) -> bool:
        """检查是否存在匹配条件的记录。"""
        stmt = select(cls.model)
        for k, v in filters.items():
            stmt = stmt.where(getattr(cls.model, k) == v)
        return (await db.execute(stmt)).scalar_one_or_none() is not None
