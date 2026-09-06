"""
表情包路由（STK）—— 列表（含收藏标记）+ 收藏/取消/我的收藏。
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from middleware.auth_middleware import get_current_user
from models.sticker import Sticker
from models.user import User
from services.sticker_service import StickerService

router = APIRouter()


def _out(s: Sticker, is_favorited: bool = False) -> dict:
    return {
        "id": s.id, "name": s.name, "emotion": s.emotion,
        "image_url": s.image_url, "category": s.category,
        "sticker_emoji": StickerService.fallback_emoji(s),
        "is_favorited": is_favorited,
    }


@router.get("")
async def list_stickers(
    emotion: str | None = Query(None, description="按情绪筛选：happy/sad/angry/neutral/love"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """表情包列表（含当前用户是否已收藏）。"""
    stmt = select(Sticker).order_by(Sticker.sort_order)
    if emotion:
        stmt = stmt.where(Sticker.emotion == emotion)
    stickers = (await db.execute(stmt)).scalars().all()
    favorited = await StickerService.get_favorited_ids(db, user.id)
    return {"data": [_out(s, s.id in favorited) for s in stickers]}


@router.get("/favorites")
async def list_favorites(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """我的收藏列表。"""
    return {"data": await StickerService.list_favorites(db, user.id)}


@router.post("/{sticker_id}/favorite")
async def favorite(
    sticker_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """收藏表情包。"""
    if not await StickerService.get(db, sticker_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="表情包不存在")
    await StickerService.favorite(db, user.id, sticker_id)
    return {"success": True, "is_favorited": True}


@router.delete("/{sticker_id}/favorite")
async def unfavorite(
    sticker_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """取消收藏。"""
    await StickerService.unfavorite(db, user.id, sticker_id)
    return {"success": True, "is_favorited": False}


@router.get("/recent")
async def get_recent_stickers(
    limit: int = Query(20, ge=1, le=100, description="返回最近使用的表情数量"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取用户最近使用的表情包列表。"""
    from dao.message_dao import MessageDAO

    recent_stickers = await MessageDAO.list_recent_stickers(db, user.id, limit)
    return {"data": recent_stickers}
