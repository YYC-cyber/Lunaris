# backend/controllers/search_controller.py
"""消息搜索 —— 全文搜索消息内容、发件人、日期范围。"""
from datetime import datetime
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from middleware.auth_middleware import get_current_user
from models.user import User
from services.search_service import SearchService
from schemas.search import (
    SearchMessagesRequest, MessageSearchResult, SearchMessagesResponse
)

router = APIRouter()


@router.get("/messages", response_model=SearchMessagesResponse)
async def search_messages(
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    from_date: Optional[datetime] = Query(None, description="开始日期（ISO 8601）"),
    to_date: Optional[datetime] = Query(None, description="结束日期（ISO 8601）"),
    user_id: Optional[str] = Query(None, description="发件人 ID（可选）"),
    limit: int = Query(50, ge=1, le=100, description="分页限制"),
    offset: int = Query(0, ge=0, description="分页偏移"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """搜索当前用户的消息（按关键词 + 可选日期范围 + 可选发件人）。"""
    try:
        if user_id:
            sender_id = uuid.UUID(user_id)
        else:
            sender_id = None
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的 user_id 格式"
        )

    results, total = await SearchService.search_messages(
        db=db,
        current_user_id=current_user.id,
        keyword=keyword,
        from_date=from_date,
        to_date=to_date,
        sender_id=sender_id,
        limit=limit,
        offset=offset,
    )

    return SearchMessagesResponse(
        data=[MessageSearchResult.from_message(msg, msg._sender) for msg in results],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/messages", response_model=SearchMessagesResponse)
async def search_messages_post(
    request: SearchMessagesRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """搜索消息（POST 版本）。"""
    try:
        sender_id = (
            uuid.UUID(request.user_id) if request.user_id else None
        )
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的 user_id 格式"
        )

    results, total = await SearchService.search_messages(
        db=db,
        current_user_id=current_user.id,
        keyword=request.keyword,
        from_date=request.from_date,
        to_date=request.to_date,
        sender_id=sender_id,
        limit=request.limit,
        offset=request.offset,
    )

    return SearchMessagesResponse(
        data=[MessageSearchResult.from_message(msg, msg._sender) for msg in results],
        total=total,
        limit=request.limit,
        offset=request.offset,
    )
