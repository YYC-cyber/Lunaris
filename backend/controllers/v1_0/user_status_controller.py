# backend/controllers/user_status_controller.py
"""在线状态 —— 用户在线状态查询、广播。"""
from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from middleware.auth_middleware import get_current_user
from models.user import User
from services.v1_0.user_status_service import UserStatusService
from schemas.v1_0.user_status import UserStatusResponse, OnlineUsersResponse

router = APIRouter()


@router.get("/online", response_model=OnlineUsersResponse)
async def get_online_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前在线用户列表。"""
    online_users = await UserStatusService.get_online_users(db)
    return OnlineUsersResponse(
        data=[
            {
                "user_id": str(user.id),
                "username": user.username,
                "nickname": user.nickname or user.username,
                "avatar_url": user.avatar_url,
                "last_seen_at": user.last_seen_at,
            }
            for user in online_users
        ],
        count=len(online_users),
    )


@router.get("/{user_id}/status", response_model=UserStatusResponse)
async def get_user_status(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取指定用户的在线状态。"""
    try:
        target_id = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的 user_id 格式"
        )

    status_info = await UserStatusService.get_user_status(db, target_id)
    if not status_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    return status_info
