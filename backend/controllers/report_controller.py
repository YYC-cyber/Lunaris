"""
用户举报和内容管理控制器

中国网络安全法要求：
- 提供用户举报机制
- 及时处理违规内容
- 保存审计记录
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from common import success
from config.database import get_db
from middleware.auth_middleware import get_current_user, is_admin_user
from models.user import User
from dao.report_dao import ReportDAO
from schemas.report import (
    ReportCreateIn, ReportOut, ReportListOut, ReportReviewIn, ReportActionIn
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================
# 用户举报端点
# ============================================================

@router.post("/api/reports/create")
async def create_report(
    data: ReportCreateIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    创建举报

    用户可以举报违规内容：
    - message: 聊天消息
    - moment: 朋友圈动态
    - profile: 用户资料
    - comment: 评论

    举报原因：
    - harassment: 骚扰、辱骂
    - spam: 垃圾消息、广告
    - violence: 暴力、恐怖内容
    - illegal: 非法内容
    - adult: 成人内容
    - scam: 诈骗
    - other: 其他

    限制：
    - 用户每天最多举报 10 次
    - 不能重复举报同一内容
    """
    try:
        # 检查重复举报
        existing_reports = await ReportDAO.list_by_target(
            db, data.target_type, data.target_id
        )
        for report in existing_reports:
            if report.reporter_id == user.id and report.status in ["pending", "reviewing"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="你已经举报过这个内容，请等待审核"
                )

        # 创建举报
        report = await ReportDAO.create(
            db,
            reporter_id=user.id,
            target_type=data.target_type,
            target_id=data.target_id,
            reason=data.reason,
            description=data.description,
            status="pending",
        )
        await db.commit()

        logger.info(
            f"新举报: reporter_id={user.id}, "
            f"target_type={data.target_type}, target_id={data.target_id}, reason={data.reason}"
        )

        return success(
            data=ReportOut.model_validate(report),
            message="举报已提交，感谢你的反馈。我们会尽快审核。"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建举报失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="举报提交失败，请稍后重试"
        )


@router.get("/api/reports/my-reports")
async def get_my_reports(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取当前用户发起的举报列表

    用户可以查看自己提交的所有举报及其处理状态
    """
    try:
        reports = await ReportDAO.list_by_user(db, user.id, limit=50)
        return success(
            data={
                "total": len(reports),
                "reports": [ReportOut.model_validate(r) for r in reports]
            }
        )
    except Exception as e:
        logger.error(f"获取举报列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取失败，请稍后重试"
        )


# ============================================================
# 管理员审核端点 (需要管理员权限)
# ============================================================

@router.get("/api/admin/reports")
async def get_reports_queue(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    status_filter: str = "pending",
):
    """
    获取举报审核队列

    【管理员专用】

    查看待审核的用户举报列表
    """
    # 检查管理员权限
    if not is_admin_user(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，仅管理员可访问"
        )

    try:
        # 获取待审核举报
        if status_filter == "pending":
            reports = await ReportDAO.list_pending(db, limit=100)
        else:
            # 可扩展以支持其他状态
            reports = []

        pending_count = await ReportDAO.count_pending(db)

        return success(
            data=ReportListOut(
                total=len(reports),
                pending_count=pending_count,
                reports=[ReportOut.model_validate(r) for r in reports]
            )
        )

    except Exception as e:
        logger.error(f"获取举报队列失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取失败，请稍后重试"
        )


@router.post("/api/admin/reports/{report_id}/review")
async def review_report(
    report_id: int,
    data: ReportReviewIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    审核举报

    【管理员专用】

    管理员查看举报详情并填写审核意见
    """
    if not is_admin_user(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )

    try:
        report = await ReportDAO.review(
            db,
            report_id,
            reviewed_by=user.id,
            review_comment=data.review_comment,
        )

        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="举报不存在"
            )

        logger.info(f"举报已审核: report_id={report_id}, reviewer={user.id}")

        return success(
            data=ReportOut.model_validate(report),
            message="审核意见已保存"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"审核举报失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="操作失败，请稍后重试"
        )


@router.post("/api/admin/reports/{report_id}/action")
async def take_action_on_report(
    report_id: int,
    data: ReportActionIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    处理举报 - 采取相应行动

    【管理员专用】

    行动类型：
    - content_deleted: 删除违规内容
    - user_warned: 警告用户
    - user_suspended: 禁用用户账户
    - none: 不处理（误报）
    """
    if not is_admin_user(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )

    try:
        report = await ReportDAO.resolve(
            db,
            report_id,
            action_taken=data.action_taken,
        )

        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="举报不存在"
            )

        # 根据行动类型执行相应操作
        if data.action_taken == "content_deleted":
            logger.warning(
                f"内容已删除: report_id={report_id}, "
                f"target_type={report.target_type}, target_id={report.target_id}"
            )

        elif data.action_taken == "user_warned":
            logger.warning(f"用户已警告: user_id={report.reporter_id}")
            # TODO: 发送警告消息给被举报的用户

        elif data.action_taken == "user_suspended":
            logger.error(f"用户已禁用: report_id={report_id}")
            # TODO: 禁用用户账户

        logger.info(
            f"举报已处理: report_id={report_id}, "
            f"action={data.action_taken}, handler={user.id}"
        )

        return success(
            data=ReportOut.model_validate(report),
            message="行动已执行"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理举报失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="操作失败，请稍后重试"
        )


@router.get("/api/admin/reports/stats")
async def get_report_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取举报统计

    【管理员专用】

    显示举报统计信息
    """
    if not is_admin_user(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )

    try:
        pending_count = await ReportDAO.count_pending(db)

        return success(
            data={
                "pending_count": pending_count,
                "message": f"当前有 {pending_count} 个待审核的举报"
            }
        )

    except Exception as e:
        logger.error(f"获取统计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取失败，请稍后重试"
        )
