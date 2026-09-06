"""
危机事件清理任务

中国 PIPL 合规：
- 定期清理超过保留期的危机事件
- 默认保留 30 天后删除

执行频率：每天凌晨 3:00
"""

import logging
from datetime import datetime

from config.database import AsyncSessionLocal
from services.emergency_handling_service import CrisisCleanupService

logger = logging.getLogger(__name__)


async def cleanup_crisis_events_task():
    """
    定期清理过期危机事件
    """
    db = AsyncSessionLocal()

    try:
        logger.info("开始清理过期危机事件...")

        deleted_count = await CrisisCleanupService.cleanup_expired_crisis_events(
            db=db,
            days_to_keep=30  # PIPL 要求的保留期
        )

        logger.info(
            f"危机事件清理完成: 删除 {deleted_count} 条记录 "
            f"(执行时间: {datetime.utcnow().isoformat()})"
        )

        return {
            "status": "success",
            "deleted_count": deleted_count,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"危机事件清理失败: {e}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

    finally:
        await db.close()
