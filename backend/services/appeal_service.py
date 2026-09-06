"""
申诉服务 —— 处理申诉业务逻辑

错误码段：
- 4004: 申诉相关异常（AppealException）
- 1002: 申诉不存在（NotFoundException）
- 1003: 权限不足（PermissionDeniedException）
"""

import uuid
from typing import List, Dict, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from dao.appeal_dao import AppealDAO
from models.appeal import Appeal
from config.logging_config import get_logger
from exceptions import (
    AppealException,
    NotFoundException,
    PermissionDeniedException,
    DatabaseException,
)

logger = get_logger("appeal_service")


class AppealService:
    """申诉服务"""

    @staticmethod
    async def create_appeal(
        db: AsyncSession,
        user_id: uuid.UUID,
        target_type: str,
        target_id: str,
        reason: str,
        report_id: Optional[int] = None,
    ) -> Appeal:
        """创建申诉"""
        try:
            appeal = await AppealDAO.create(
                db,
                user_id=user_id,
                report_id=report_id,
                target_type=target_type,
                target_id=target_id,
                reason=reason,
                status="pending",
            )
            logger.info(
                "Appeal created",
                extra={
                    "appeal_id": appeal.id,
                    "user_id": user_id,
                    "target_type": target_type,
                    "target_id": target_id,
                }
            )
            return appeal
        except IntegrityError as e:
            logger.error(
                f"Database integrity error when creating appeal: {str(e)}",
                extra={"user_id": user_id, "target_type": target_type},
                exc_info=True
            )
            raise DatabaseException("申诉创建失败", detail=str(e))
        except Exception as e:
            logger.error(
                f"Failed to create appeal: {str(e)}",
                extra={"user_id": user_id, "target_type": target_type},
                exc_info=True
            )
            raise AppealException("申诉创建失败，请稍后重试")

    @staticmethod
    async def get_user_appeals(
        db: AsyncSession,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[Appeal], int]:
        """获取用户的申诉列表"""
        try:
            appeals = await AppealDAO.list_by_user(db, user_id, limit=limit, offset=offset)
            total = await AppealDAO.count(db, user_id=user_id)
            logger.info(
                "User appeals retrieved",
                extra={"user_id": user_id, "count": len(appeals), "total": total}
            )
            return appeals, total
        except Exception as e:
            logger.error(
                f"Failed to fetch user appeals: {str(e)}",
                extra={"user_id": user_id},
                exc_info=True
            )
            raise AppealException("获取申诉列表失败，请稍后重试")

    @staticmethod
    async def get_pending_appeals(
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[Appeal], int]:
        """获取待审核的申诉"""
        try:
            appeals = await AppealDAO.list_pending(db, limit=limit, offset=offset)
            total = await AppealDAO.count_by_status(db, "pending")
            logger.info(
                "Pending appeals retrieved",
                extra={"count": len(appeals), "total": total}
            )
            return appeals, total
        except Exception as e:
            logger.error(
                f"Failed to fetch pending appeals: {str(e)}",
                exc_info=True
            )
            raise AppealException("获取申诉队列失败，请稍后重试")

    @staticmethod
    async def review_appeal(
        db: AsyncSession,
        appeal_id: int,
        reviewed_by: uuid.UUID,
        approved: bool,
        admin_comment: str,
    ) -> Optional[Appeal]:
        """审核申诉

        事务处理：审核申诉时涉及单个记录更新，所有更改原子性执行。
        """
        try:
            async with db.begin():
                result = await AppealDAO.review(
                    db,
                    appeal_id,
                    reviewed_by=reviewed_by,
                    approved=approved,
                    admin_comment=admin_comment,
                )
            if not result:
                logger.warning(
                    f"Appeal not found for review",
                    extra={"appeal_id": appeal_id, "reviewed_by": reviewed_by}
                )
                raise NotFoundException("Appeal", appeal_id)

            logger.info(
                "Appeal reviewed",
                extra={
                    "appeal_id": appeal_id,
                    "reviewed_by": reviewed_by,
                    "approved": approved,
                }
            )
            return result
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(
                f"Failed to review appeal {appeal_id}: {str(e)}",
                extra={"appeal_id": appeal_id, "reviewed_by": reviewed_by},
                exc_info=True
            )
            raise AppealException("申诉审核失败，请稍后重试")

    @staticmethod
    async def get_appeal_stats(db: AsyncSession) -> Dict[str, int]:
        """获取申诉统计"""
        try:
            stats = await AppealDAO.get_stats(db)
            logger.debug(
                "Appeal stats retrieved",
                extra={"stats": stats}
            )
            return stats
        except Exception as e:
            logger.error(
                f"Failed to fetch appeal stats: {str(e)}",
                exc_info=True
            )
            raise AppealException("获取统计数据失败，请稍后重试")
