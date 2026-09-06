# backend/tasks/log_cleanup_task.py
"""清理3个月前的系统日志"""

from datetime import datetime, timedelta
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from config.settings import get_settings
from models.system_log import SystemLog
import logging

logger = logging.getLogger("log_cleanup")

async def cleanup_old_logs() -> None:
    """删除3个月前的日志"""
    try:
        settings = get_settings()
        engine = create_async_engine(settings.DATABASE_URL, echo=False)

        async with engine.begin() as conn:
            # 计算3个月前的日期
            three_months_ago = datetime.now() - timedelta(days=90)

            # 删除3个月前的日志
            stmt = delete(SystemLog).where(SystemLog.created_at < three_months_ago)
            result = await conn.execute(stmt)

            deleted_count = result.rowcount
            logger.info(f"✅ 日志清理完成: 删除了 {deleted_count} 条旧日志（超过3个月）")

        await engine.dispose()
    except Exception as e:
        logger.error(f"❌ 日志清理失败: {e}")
