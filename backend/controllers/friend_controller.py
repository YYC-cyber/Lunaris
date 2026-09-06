# backend/controllers/friend_controller.py
"""好友路由 —— 按 lunaris_id 搜索/添加真人好友。"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from middleware.auth_middleware import get_current_user
from models.user import User
from services.friend_service import FriendService

router = APIRouter()


class LunarisIdIn(BaseModel):
    lunaris_id: str


class HandleIn(BaseModel):
    user_id: str
    action: str  # accept / reject


def _user_out(user: User) -> dict:
    return {
        "user_id": str(user.id),
        "lunaris_id": user.lunaris_id,
        "nickname": user.nickname or user.username,
        "avatar_url": user.avatar_url,
    }


@router.get("/search")
async def search_user(
    lunaris_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """按 lunaris_id 搜索用户（返回可添加的用户信息）。"""
    target = await FriendService.search_by_lunaris_id(db, user.id, lunaris_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到该用户")
    return _user_out(target)


@router.post("/request")
async def send_request(
    data: LunarisIdIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """按 lunaris_id 发送好友申请（对方先申请过你 → 直接互为好友）。"""
    target = await FriendService.search_by_lunaris_id(db, user.id, data.lunaris_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到该用户")
    try:
        rel = await FriendService.send_request(db, user.id, target.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {"success": True, "user_id": str(target.id), "status": rel.status}


@router.post("/request/handle")
async def handle_request(
    data: HandleIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """处理收到的好友申请（accept / reject）。"""
    try:
        friend_id = uuid.UUID(data.user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效 user_id")
    try:
        await FriendService.handle_request(db, user.id, friend_id, data.action)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {"success": True, "action": data.action}


@router.get("")
async def list_friends(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """我的好友列表。"""
    friends = await FriendService.list_friends(db, user.id)
    return {"data": [_user_out(f) for f in friends]}


@router.get("/requests")
async def list_requests(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """我收到待处理的好友申请。"""
    return {"data": await FriendService.list_pending_requests(db, user.id)}


@router.delete("/{friend_id}")
async def remove_friend(
    friend_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除好友。"""
    try:
        fid = uuid.UUID(friend_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效 user_id")
    try:
        await FriendService.remove_friend(db, user.id, fid)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {"success": True}
