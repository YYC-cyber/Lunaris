"""
应急和违规处理服务

中国网络安全法和 PIPL 合规：
1. 危机事件自动清理（30天后删除）
2. 违规内容自动标记和处理
3. 用户警告和封禁机制
"""

from datetime import datetime, timedelta
import logging
import uuid
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class CrisisCleanupService:
    """危机事件清理服务"""

    @staticmethod
    async def cleanup_expired_crisis_events(
        db: AsyncSession,
        days_to_keep: int = 30
    ) -> int:
        """
        自动删除超过指定天数的危机事件

        PIPL 合规：敏感信息应有保留期限
        默认：30天后删除

        事务处理：批量删除操作作为单一事务执行。

        Args:
            db: 数据库连接
            days_to_keep: 保留天数（默认 30）

        Returns:
            删除的记录数
        """
        from models.v1_0.crisis_event import CrisisEvent

        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        try:
            async with db.begin():
                result = await db.execute(
                    delete(CrisisEvent).where(
                        CrisisEvent.handled_at < cutoff_date
                    )
                )
                deleted_count = result.rowcount or 0

            if deleted_count > 0:
                logger.info(f"已清理 {deleted_count} 条过期危机事件（{days_to_keep}天前）")

            return deleted_count

        except Exception as e:
            logger.error(f"危机事件清理失败: {e}")
            return 0


class ViolationHandlingService:
    """违规内容处理服务"""

    @staticmethod
    async def warn_user(
        db: AsyncSession,
        user_id: uuid.UUID,
        reason: str,
        message: str = None
    ) -> bool:
        """
        警告用户违反服务条款

        Args:
            db: 数据库连接
            user_id: 用户 ID
            reason: 警告原因
            message: 警告信息

        Returns:
            是否成功
        """
        try:
            from models.user import User

            user = await db.execute(
                select(User).where(User.id == user_id)
            )
            user = user.scalar_one_or_none()

            if not user:
                return False

            # TODO: 记录用户警告，可能需要建立 violation 表
            # TODO: 发送警告消息给用户

            logger.warning(
                f"用户已警告: user_id={user_id}, reason={reason}"
            )
            return True

        except Exception as e:
            logger.error(f"警告用户失败: {e}")
            return False

    @staticmethod
    async def suspend_user(
        db: AsyncSession,
        user_id: uuid.UUID,
        reason: str,
        duration_hours: int = 24
    ) -> bool:
        """
        暂时禁用用户账户

        事务处理：用户状态更新作为单一原子操作执行。

        Args:
            db: 数据库连接
            user_id: 用户 ID
            reason: 禁用原因
            duration_hours: 禁用时长（小时）

        Returns:
            是否成功
        """
        try:
            from models.user import User

            suspend_until = datetime.utcnow() + timedelta(hours=duration_hours)

            async with db.begin():
                result = await db.execute(
                    update(User)
                    .where(User.id == user_id)
                    .values(
                        is_active=False,
                    )
                )

            logger.warning(
                f"用户已禁用: user_id={user_id}, reason={reason}, "
                f"duration={duration_hours}小时"
            )

            return result.rowcount > 0

        except Exception as e:
            logger.error(f"禁用用户失败: {e}")
            return False

    @staticmethod
    async def delete_content(
        db: AsyncSession,
        content_type: str,
        content_id: int
    ) -> bool:
        """
        删除违规内容

        事务处理：不同内容类型的删除都作为原子操作执行。

        Args:
            db: 数据库连接
            content_type: 内容类型 (message/moment/comment)
            content_id: 内容 ID

        Returns:
            是否成功
        """
        try:
            async with db.begin():
                if content_type == "message":
                    from models.v1_0.message import Message
                    result = await db.execute(
                        delete(Message).where(Message.id == content_id)
                    )

                elif content_type == "moment":
                    from models.v1_0.moment import Moment
                    result = await db.execute(
                        delete(Moment).where(Moment.id == content_id)
                    )

                elif content_type == "comment":
                    from models.v1_0.comment import Comment
                    result = await db.execute(
                        delete(Comment).where(Comment.id == content_id)
                    )

                else:
                    logger.warning(f"未知的内容类型: {content_type}")
                    return False

            logger.warning(
                f"违规内容已删除: type={content_type}, id={content_id}"
            )

            return result.rowcount > 0

        except Exception as e:
            logger.error(f"删除内容失败: {e}")
            return False

    @staticmethod
    async def flag_content(
        db: AsyncSession,
        content_type: str,
        content_id: int,
        reason: str
    ) -> bool:
        """
        标记内容为需要审查

        Args:
            db: 数据库连接
            content_type: 内容类型
            content_id: 内容 ID
            reason: 标记原因

        Returns:
            是否成功
        """
        try:
            # TODO: 添加 content_flag 表来记录需要审查的内容
            logger.info(
                f"内容已标记审查: type={content_type}, id={content_id}, reason={reason}"
            )
            return True

        except Exception as e:
            logger.error(f"标记内容失败: {e}")
            return False


class AbusePreventionService:
    """滥用防止服务"""

    @staticmethod
    async def check_spam_risk(
        db: AsyncSession,
        user_id: uuid.UUID,
        message_count_in_minutes: int = 10,
        threshold: int = 5
    ) -> bool:
        """
        检查用户是否在短时间内发送大量消息（垃圾风险）

        Args:
            db: 数据库连接
            user_id: 用户 ID
            message_count_in_minutes: 检查时间窗口（分钟）
            threshold: 触发警告的消息数阈值

        Returns:
            是否存在垃圾风险
        """
        try:
            from models.v1_0.message import Message
            from datetime import datetime, timedelta

            cutoff_time = datetime.utcnow() - timedelta(minutes=message_count_in_minutes)

            result = await db.execute(
                select(Message).where(
                    Message.user_id == user_id,
                    Message.created_at > cutoff_time
                )
            )

            recent_messages = result.scalars().all()
            is_spam = len(recent_messages) > threshold

            if is_spam:
                logger.warning(
                    f"检测到垃圾消息风险: user_id={user_id}, "
                    f"消息数={len(recent_messages)}/{threshold}"
                )

            return is_spam

        except Exception as e:
            logger.error(f"垃圾检查失败: {e}")
            return False

    @staticmethod
    async def check_rate_limit_violation(
        user_id: uuid.UUID,
        action: str,
        limit: int,
        window_minutes: int = 1
    ) -> bool:
        """
        检查用户是否超过限流阈值

        Args:
            user_id: 用户 ID
            action: 操作类型 (message/report/comment)
            limit: 允许的最大次数
            window_minutes: 时间窗口（分钟）

        Returns:
            是否超过限制
        """
        # TODO: 实现基于 Redis 或内存的计数器
        # 这是一个占位实现
        return False


# 简单的内存 rate limiter（单进程，重启重置）
_rate_limit_counters: dict = {}


async def rate_limit_action(
    db: AsyncSession,
    user_id: str,
    action: str,
    max_count: int = 10,
    time_window_seconds: int = 60,
) -> bool:
    """
    速率限制检查（简单的内存实现）。

    Args:
        db: 数据库连接（保留参数便于未来迁移到 Redis）
        user_id: 用户 ID
        action: 操作类型
        max_count: 时间窗口内最大次数
        time_window_seconds: 时间窗口（秒）

    Returns:
        True 表示允许，False 表示超限
    """
    from datetime import datetime, timezone

    key = f"{user_id}:{action}"
    now = datetime.now(timezone.utc)

    if key not in _rate_limit_counters:
        _rate_limit_counters[key] = {"count": 1, "reset_at": now.timestamp() + time_window_seconds}
        return True

    counter = _rate_limit_counters[key]

    # 检查时间窗口是否过期
    if now.timestamp() >= counter["reset_at"]:
        _rate_limit_counters[key] = {"count": 1, "reset_at": now.timestamp() + time_window_seconds}
        return True

    # 增加计数
    counter["count"] += 1
    return counter["count"] <= max_count
