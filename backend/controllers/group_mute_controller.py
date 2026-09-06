"""群组禁言控制器"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from middleware.auth_middleware import get_current_user
from models.user import User
from services.group_mute_service import GroupMuteService
from services.group_chat_service import GroupChatService
from dao.group_chat_dao import GroupMemberDAO
from schemas.group_mute import GroupMuteRequest, MutedUsersListOut, MuteUserOut

router = APIRouter()


@router.post("/groups/{group_id}/mute/{user_id}")
async def mute_user(
    group_id: int,
    user_id: str,
    duration_minutes: int = Query(60, ge=1),
    operator: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """禁言用户"""
    muted_user_id = uuid.UUID(user_id)

    # 检查群聊是否存在
    group_info = await GroupChatService.get_group_info(db, group_id)
    if not group_info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="群聊不存在")

    # 检查操作者是否有权限
    operator_member = None
    for member in group_info.get("members", []):
        if member.get("user_id") == str(operator.id):
            operator_member = member
            break

    if not operator_member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="你不是群成员")

    # 只有群主和管理员可以禁言
    if operator_member.get("role") not in ["owner", "admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")

    # 不能禁言自己
    if muted_user_id == operator.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能禁言自己")

    # 添加禁言记录
    mute = await GroupMuteService.mute(db, group_id, muted_user_id, duration_minutes, operator.id)
    await db.commit()

    return {
        "mute_id": mute.id,
        "user_id": str(mute.muted_user_id),
        "muted_until": mute.muted_until.isoformat(),
        "message": "禁言成功",
    }


@router.delete("/groups/{group_id}/mute/{user_id}")
async def unmute_user(
    group_id: int,
    user_id: str,
    operator: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """解除禁言"""
    muted_user_id = uuid.UUID(user_id)

    # 检查群聊是否存在
    group_info = await GroupChatService.get_group_info(db, group_id)
    if not group_info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="群聊不存在")

    # 检查操作者是否有权限
    operator_member = None
    for member in group_info.get("members", []):
        if member.get("user_id") == str(operator.id):
            operator_member = member
            break

    if not operator_member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="你不是群成员")

    # 只有群主和管理员可以解除禁言
    if operator_member.get("role") not in ["owner", "admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")

    # 移除禁言
    await GroupMuteService.unmute(db, group_id, muted_user_id)
    await db.commit()

    return {"message": "解除禁言成功"}


@router.get("/groups/{group_id}/muted-users")
async def list_muted_users(
    group_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MutedUsersListOut:
    """获取禁言用户列表"""
    # 检查群聊是否存在
    group_info = await GroupChatService.get_group_info(db, group_id)
    if not group_info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="群聊不存在")

    # 检查用户是否是群成员
    is_member = await GroupMemberDAO.is_member(db, group_id, user.id)
    if not is_member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="你不是群成员")

    # 获取禁言列表
    muted_users, total = await GroupMuteService.list_muted_users(db, group_id, skip, limit)

    return MutedUsersListOut(
        users=muted_users,
        total=total,
        skip=skip,
        limit=limit,
    )
