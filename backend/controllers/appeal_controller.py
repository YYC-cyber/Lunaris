"""
申诉管理控制器

用户申诉端点 + 管理员审核端点
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from common import success
from config.database import get_db
from middleware.auth_middleware import get_current_user, is_admin_user
from models.user import User
from services.appeal_service import AppealService
from schemas.appeal import (
    AppealCreateRequest, AppealReviewRequest, AppealOut,
    AppealListOut, AppealStatsOut
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================
# 用户申诉端点
# ============================================================

@router.post("/api/appeals/create")
async def create_appeal(
    data: AppealCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    创建申诉

    用户可以对以下决定申诉：
    - 内容被删除
    - 账户被禁用
    - 被举报处理
    """
    try:
        appeal = await AppealService.create_appeal(
            db,
            user_id=user.id,
            target_type=data.target_type,
            target_id=data.target_id,
            reason=data.reason,
            report_id=data.report_id,
        )

        logger.info(
            f"新申诉: user_id={user.id}, "
            f"target_type={data.target_type}, target_id={data.target_id}"
        )

        return success(
            data=AppealOut.model_validate(appeal),
            message="申诉已提交，感谢你的反馈。我们会尽快审核。"
        )

    except Exception as e:
        logger.error(f"创建申诉失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="申诉提交失败，请稍后重试"
        )


@router.get("/api/appeals/my")
async def get_my_appeals(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取当前用户发起的申诉列表

    用户可以查看自己提交的所有申诉及其审核状态
    """
    try:
        appeals, total = await AppealService.get_user_appeals(
            db, user.id, limit=limit, offset=offset
        )
        return success(
            data=AppealListOut(
                total=total,
                appeals=[AppealOut.model_validate(a) for a in appeals]
            )
        )
    except Exception as e:
        logger.error(f"获取申诉列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取失败，请稍后重试"
        )


# ============================================================
# 管理员审核端点 (需要管理员权限)
# ============================================================

@router.get("/api/admin/appeals")
async def get_pending_appeals(
    status_filter: str = Query("pending", description="申诉状态"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取申诉审核队列

    【管理员专用】

    查看待审核的用户申诉列表
    """
    # 检查管理员权限
    if not is_admin_user(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，仅管理员可访问"
        )

    try:
        if status_filter == "pending":
            appeals, total = await AppealService.get_pending_appeals(
                db, limit=limit, offset=offset
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="当前仅支持 pending 状态"
            )

        return success(
            data=AppealListOut(
                total=total,
                appeals=[AppealOut.model_validate(a) for a in appeals]
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取申诉队列失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取失败，请稍后重试"
        )


@router.post("/api/admin/appeals/{appeal_id}/review")
async def review_appeal(
    appeal_id: int,
    data: AppealReviewRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    审核申诉

    【管理员专用】

    管理员查看申诉详情并填写审核意见
    """
    if not is_admin_user(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )

    try:
        appeal = await AppealService.review_appeal(
            db,
            appeal_id,
            reviewed_by=user.id,
            approved=data.approved,
            admin_comment=data.comment,
        )

        if not appeal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="申诉不存在"
            )

        logger.info(
            f"申诉已审核: appeal_id={appeal_id}, "
            f"approved={data.approved}, reviewer={user.id}"
        )

        return success(
            data=AppealOut.model_validate(appeal),
            message="审核意见已保存"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"审核申诉失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="操作失败，请稍后重试"
        )


@router.get("/api/admin/appeals/stats")
async def get_appeal_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取申诉统计

    【管理员专用】

    显示申诉统计信息
    """
    if not is_admin_user(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )

    try:
        stats = await AppealService.get_appeal_stats(db)
        return success(data=AppealStatsOut(**stats))

    except Exception as e:
        logger.error(f"获取统计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取失败，请稍后重试"
        )
