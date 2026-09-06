"""
事务管理器 —— 统一处理复杂的多操作事务

本模块提供了便利的上下文管理器和装饰器，用于安全地处理涉及多个 DAO
操作的事务，确保 ACID 特性。

【使用场景】
1. 单个 DAO 操作：通常 DAO 方法内部自动 commit，无需处理事务
2. 多个 DAO 操作（原子性）：使用事务管理器或 db.begin()
3. 需要手动控制 commit/rollback：使用事务管理器的上下文管理器

【示例】

### 方法 1：使用 async_with db.begin()（推荐）
```python
async def create_and_send_email(db, user_email):
    async with db.begin():
        user = await UserDAO.create(db, email=user_email)
        await EmailDAO.create(db, user_id=user.id, subject="Welcome")
    # 出作用域时自动 commit；异常时自动 rollback
```

### 方法 2：使用 with_transaction 包装函数
```python
async def complex_operation(db):
    async def operation(db):
        user = await UserDAO.create(db, email="test@test.com")
        await EmailDAO.create(db, user_id=user.id)
        return user

    return await with_transaction(db, operation)
```

### 方法 3：使用 @transactional 装饰器
```python
class UserService:
    @transactional()
    async def create_user_with_email(db, email):
        user = await UserDAO.create(db, email=email)
        await EmailDAO.create(db, user_id=user.id)
        return user
```
"""

import logging
from functools import wraps
from typing import Callable, TypeVar, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class TransactionError(Exception):
    """事务处理异常"""
    pass


async def with_transaction(
    db: AsyncSession,
    coro: Callable[[AsyncSession], Any],
    on_error: Optional[Callable[[Exception], None]] = None,
) -> Any:
    """
    在事务中执行异步操作。

    Args:
        db: 数据库会话
        coro: 异步函数，接收 db 作为参数
        on_error: 错误处理回调（可选）

    Returns:
        异步操作的结果

    Raises:
        TransactionError: 事务失败时抛出

    【示例】
    ```python
    async def create_user(db):
        return await UserDAO.create(db, name='Alice')

    user = await with_transaction(db, create_user)
    ```
    """
    try:
        async with db.begin():
            return await coro(db)
    except SQLAlchemyError as e:
        logger.error(f"数据库事务失败: {e}")
        if on_error:
            on_error(e)
        raise TransactionError(f"事务执行失败: {e}") from e
    except Exception as e:
        logger.error(f"事务中发生异常: {e}")
        if on_error:
            on_error(e)
        raise


def transactional():
    """
    装饰器：将异步函数包装在事务中。

    在被装饰的函数中，如果任何操作失败，所有更改都会自动回滚。

    【示例】
    ```python
    @transactional()
    async def create_user_with_settings(db, email):
        user = await UserDAO.create(db, email=email)
        await UserSettingsDAO.create(db, user_id=user.id, theme='dark')
        return user
    ```

    【注意】
    - 被装饰函数必须是异步函数
    - 第一个参数必须是 AsyncSession（db）
    - 异常时自动回滚，不需要手动处理
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # 提取 db 参数
            db = None
            if args:
                db = args[0]
            elif 'db' in kwargs:
                db = kwargs['db']
            else:
                raise TransactionError("找不到 db 参数")

            if not isinstance(db, AsyncSession):
                raise TransactionError(f"期望 AsyncSession，实际是 {type(db)}")

            async def operation(db_):
                return await func(*args, **kwargs)

            return await with_transaction(db, operation)

        return wrapper
    return decorator


async def safe_delete(
    db: AsyncSession,
    obj: Any,
    cascade: bool = False,
    on_error: Optional[Callable[[Exception], None]] = None,
) -> bool:
    """
    安全删除对象，支持级联删除和错误处理。

    Args:
        db: 数据库会话
        obj: 要删除的对象
        cascade: 是否执行级联删除检查
        on_error: 错误处理回调

    Returns:
        删除是否成功

    【示例】
    ```python
    success = await safe_delete(db, user_obj)
    if not success:
        logger.error("删除用户失败")
    ```
    """
    try:
        async with db.begin():
            # 如果需要级联检查，在这里可以添加
            if cascade:
                # TODO: 实现级联删除前的检查逻辑
                pass
            await db.delete(obj)
        return True
    except SQLAlchemyError as e:
        logger.error(f"删除对象失败: {e}")
        if on_error:
            on_error(e)
        return False
    except Exception as e:
        logger.error(f"删除过程中发生异常: {e}")
        if on_error:
            on_error(e)
        return False


async def safe_update(
    db: AsyncSession,
    obj: Any,
    updates: dict,
    on_error: Optional[Callable[[Exception], None]] = None,
) -> Optional[Any]:
    """
    安全更新对象字段，自动处理事务。

    Args:
        db: 数据库会话
        obj: 要更新的对象
        updates: 字段更新字典
        on_error: 错误处理回调

    Returns:
        更新后的对象，失败返回 None

    【示例】
    ```python
    user = await safe_update(
        db,
        user_obj,
        {"status": "active", "updated_at": datetime.utcnow()}
    )
    ```
    """
    try:
        async with db.begin():
            for key, value in updates.items():
                setattr(obj, key, value)
            await db.refresh(obj)
        return obj
    except SQLAlchemyError as e:
        logger.error(f"更新对象失败: {e}")
        if on_error:
            on_error(e)
        return None
    except Exception as e:
        logger.error(f"更新过程中发生异常: {e}")
        if on_error:
            on_error(e)
        return None


class TransactionContext:
    """
    事务上下文管理器 —— 手动控制事务边界。

    【示例】
    ```python
    async with TransactionContext(db) as txn:
        user = await UserDAO.create(db, name='Alice')
        await EmailDAO.create(db, user_id=user.id)
        # 出作用域时自动 commit；异常时自动 rollback
    ```
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._transaction = None

    async def __aenter__(self) -> AsyncSession:
        self._transaction = await self.db.begin()
        return self.db

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logger.error(f"事务异常，自动回滚: {exc_val}")
            await self._transaction.rollback()
            return False  # 继续抛出异常
        else:
            try:
                await self._transaction.commit()
            except Exception as e:
                logger.error(f"事务提交失败: {e}")
                await self._transaction.rollback()
                raise
