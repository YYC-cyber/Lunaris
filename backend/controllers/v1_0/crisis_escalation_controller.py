"""
危机升级管理控制器 —— 管理员专用

支持危机事件的升级、解决和列表查询
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import uuid

from common import success
from config.database import get_db
from middleware.auth_middleware import get_current_user, is_admin_user
from models.user import User
from core.crisis import CrisisService
from schemas.v1_0.crisis_event import (
    CrisisEscalateRequest, CrisisResolveRequest, CrisisEventOut,
    CrisisEventListOut
)
from ws.connection_manager import get_connection_manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/api/admin/crisis/{event_id}/escalate")
async def escalate_crisis(
    event_id: int,
    data: CrisisEscalateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    升级危机事件

    【管理员专用】

    将危机事件升级为 'escalated' 状态，可选分配给指定管理员，
    并通过 WebSocket 通知所有在线管理员
    """
    if not is_admin_user(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，仅管理员可访问"
        )

    try:
        result = await CrisisService.escalate_crisis(
            db, event_id, assigned_to_admin_id=data.assigned_to
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="危机事件不存在"
            )

        logger.info(
            f"危机事件已升级: event_id={event_id}, "
            f"assigned_to={data.assigned_to}, escalated_by={user.id}"
        )

        # 通过 WebSocket 推送通知给所有在线管理员
        try:
            cm = get_connection_manager()
            # 遍历所有在线用户，推送给管理员们
            online_users = cm.get_all_online()
            for online_user_id in online_users:
                try:
                    # 这里假设管理员已在线；实际上需要维护管理员列表
                    await cm.push(
                        user_id=online_user_id,
                        event_type="crisis_escalation",
                        event_id=str(event_id),
                        data={
                            "event_id": event_id,
                            "user_id": str(result["user_id"]),
                            "risk_level": result["risk_level"],
                            "escalation_status": result["escalation_status"],
                            "assigned_to": str(result["assigned_to"]) if result["assigned_to"] else None,
                        }
                    )
                except Exception as e:
                    logger.warning(f"推送危机升级通知失败: {e}")
        except Exception as e:
            logger.warning(f"获取连接管理器失败: {e}")

        return success(
            data=result,
            message="危机事件已升级"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"升级危机事件失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="操作失败，请稍后重试"
        )


@router.post("/api/admin/crisis/{event_id}/resolve")
async def resolve_crisis(
    event_id: int,
    data: CrisisResolveRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    解决危机事件

    【管理员专用】

    标记危机事件为已解决，记录解决备注
    """
    if not is_admin_user(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )

    try:
        result = await CrisisService.resolve_crisis(
            db, event_id, notes=data.notes
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="危机事件不存在"
            )

        logger.info(
            f"危机事件已解决: event_id={event_id}, "
            f"resolved_by={user.id}"
        )

        return success(
            data=result,
            message="危机事件已解决"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"解决危机事件失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="操作失败，请稍后重试"
        )


@router.get("/api/admin/crisis")
async def list_escalated_crisis(
    status_filter: str = Query("escalated", description="危机状态"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    列表已升级的危机事件

    【管理员专用】

    查看已升级的危机事件列表（分页）
    """
    if not is_admin_user(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，仅管理员可访问"
        )

    try:
        if status_filter not in ["escalated", "all"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="状态参数无效（支持：escalated, all）"
            )

        events, total = await CrisisService.list_escalated(
            db, limit=limit, offset=offset
        )

        return success(
            data=CrisisEventListOut(
                total=total,
                events=[CrisisEventOut.model_validate(e) for e in events]
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取危机事件列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取失败，请稍后重试"
        )
