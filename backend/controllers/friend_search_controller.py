# backend/controllers/friend_search_controller.py
"""用户搜索 —— 带筛选条件（性别、活跃度、排序）。"""
from datetime import datetime
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from middleware.auth_middleware import get_current_user
from models.user import User
from services.friend_service import FriendService
from schemas.friend_search import UserSearchResult, UserSearchResponse

router = APIRouter()


@router.get("/search", response_model=UserSearchResponse)
async def search_users(
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    gender: Optional[str] = Query(None, pattern="^(male|female)$", description="性别筛选"),
    active_after: Optional[datetime] = Query(None, description="最后活跃时间（ISO 8601）"),
    sort: str = Query("activity", pattern="^(name|activity|added)$", description="排序方式"),
    limit: int = Query(50, ge=1, le=100, description="分页限制"),
    offset: int = Query(0, ge=0, description="分页偏移"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """搜索用户（支持性别、活跃度筛选和多种排序）。"""
    results, total = await FriendService.search_users(
        db=db,
        keyword=keyword,
        gender=gender,
        active_after=active_after,
        sort_by=sort,
        limit=limit,
        offset=offset,
    )

    return UserSearchResponse(
        data=[UserSearchResult.from_user(user) for user in results],
        total=total,
        limit=limit,
        offset=offset,
    )
