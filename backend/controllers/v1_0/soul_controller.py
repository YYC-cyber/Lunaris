# backend/controllers/soul_controller.py
"""角色 / 好友路由。所有接口从 JWT token 取当前用户身份。"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from middleware.auth_middleware import get_current_user
from models.user import User
from schemas.v1_0.soul import SoulOut
from services.v1_0.soul_service import SoulService

router = APIRouter()


@router.get("/paired", response_model=list[SoulOut])
async def get_paired_souls(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户已配对的角色列表。"""
    return await SoulService.get_paired_soul_items(db, user.id)


@router.get("/available", response_model=list[SoulOut])
async def get_available_souls(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取可添加的异性角色（广场）。"""
    souls = await SoulService.get_available_souls(db, user.id, user.gender)
    return [SoulOut.model_validate(s) for s in souls]


@router.post("/{soul_id}/add")
async def add_soul(
    soul_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """添加角色为好友（SOUL-03），并触发 AI 开场白（SOUL-05）。"""
    try:
        friendship = await SoulService.add_soul(db, user.id, user.gender, soul_id)
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {"success": True, "soul_id": soul_id, "is_primary": friendship.is_primary}


@router.put("/{soul_id}/primary")
async def set_primary(
    soul_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """设为默认伴侣（SOUL-04）。"""
    try:
        await SoulService.set_primary(db, user.id, soul_id)
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {"success": True, "soul_id": soul_id}


@router.delete("/{soul_id}/remove")
async def remove_soul(
    soul_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除好友。"""
    try:
        await SoulService.remove_soul(db, user.id, soul_id)
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {"success": True, "soul_id": soul_id}
