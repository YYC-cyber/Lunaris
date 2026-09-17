"""群组公告控制器"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from middleware.auth_middleware import get_current_user
from models.user import User
from services.v1_0.group_announcement_service import GroupAnnouncementService
from services.v1_0.group_chat_service import GroupChatService
from dao.v1_0.group_chat_dao import GroupMemberDAO
from schemas.v1_0.group_announcement import (
    GroupAnnouncementCreateRequest,
    GroupAnnouncementOut,
    AnnouncementsListOut,
)

router = APIRouter()


@router.post("/groups/{group_id}/announcements")
async def create_announcement(
    group_id: int,
    req: GroupAnnouncementCreateRequest,
    operator: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GroupAnnouncementOut:
    """创建公告（仅管理员及以上可操作）"""
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

    # 只有群主和管理员可以创建公告
    if operator_member.get("role") not in ["owner", "admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")

    # 创建公告
    announcement = await GroupAnnouncementService.create(
        db,
        group_id=group_id,
        content=req.content,
        created_by=operator.id,
    )
    await db.commit()

    return GroupAnnouncementOut(
        id=announcement.id,
        group_id=announcement.group_id,
        content=announcement.content,
        created_by=str(announcement.created_by),
        is_pinned=announcement.is_pinned,
        created_at=announcement.created_at.isoformat(),
        updated_at=announcement.updated_at.isoformat(),
    )


@router.delete("/groups/{group_id}/announcements/{announcement_id}")
async def delete_announcement(
    group_id: int,
    announcement_id: int,
    operator: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除公告（仅创建者可操作）"""
    # 检查群聊是否存在
    group_info = await GroupChatService.get_group_info(db, group_id)
    if not group_info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="群聊不存在")

    # 获取公告
    from dao.v1_0.group_announcement_dao import GroupAnnouncementDAO

    announcement = await GroupAnnouncementDAO.get(db, announcement_id)
    if not announcement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="公告不存在")

    if announcement.group_id != group_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="公告不存在")

    # 检查权限（创建者或群主可删除）
    if announcement.created_by != operator.id and group_info.get("creator_id") != str(operator.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")

    # 删除公告
    await GroupAnnouncementService.delete(db, announcement_id)
    await db.commit()

    return {"message": "删除成功"}


@router.get("/groups/{group_id}/announcements")
async def list_announcements(
    group_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnnouncementsListOut:
    """获取公告列表（分页，置顶优先）"""
    # 检查群聊是否存在
    group_info = await GroupChatService.get_group_info(db, group_id)
    if not group_info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="群聊不存在")

    # 检查用户是否是群成员
    is_member = await GroupMemberDAO.is_member(db, group_id, user.id)
    if not is_member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="你不是群成员")

    # 获取公告列表
    announcements, total = await GroupAnnouncementService.list_by_group(db, group_id, skip, limit)

    announcement_list = [
        GroupAnnouncementOut(
            id=ann.id,
            group_id=ann.group_id,
            content=ann.content,
            created_by=str(ann.created_by),
            is_pinned=ann.is_pinned,
            created_at=ann.created_at.isoformat(),
            updated_at=ann.updated_at.isoformat(),
        )
        for ann in announcements
    ]

    return AnnouncementsListOut(
        announcements=announcement_list,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.patch("/groups/{group_id}/announcements/{announcement_id}/pin")
async def toggle_announcement_pin(
    group_id: int,
    announcement_id: int,
    is_pinned: bool = Query(...),
    operator: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GroupAnnouncementOut:
    """切换公告置顶状态（仅管理员及以上可操作）"""
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

    # 只有群主和管理员可以置顶公告
    if operator_member.get("role") not in ["owner", "admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")

    # 获取公告
    from dao.v1_0.group_announcement_dao import GroupAnnouncementDAO

    announcement = await GroupAnnouncementDAO.get(db, announcement_id)
    if not announcement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="公告不存在")

    if announcement.group_id != group_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="公告不存在")

    # 切换置顶状态
    announcement = await GroupAnnouncementService.toggle_pin(db, announcement_id, is_pinned)
    await db.commit()

    return GroupAnnouncementOut(
        id=announcement.id,
        group_id=announcement.group_id,
        content=announcement.content,
        created_by=str(announcement.created_by),
        is_pinned=announcement.is_pinned,
        created_at=announcement.created_at.isoformat(),
        updated_at=announcement.updated_at.isoformat(),
    )
