# backend/controllers/ui_preference_controller.py
"""UI 偏好设置控制器"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from middleware.auth_middleware import get_current_user
from models.user import User
from schemas.ui_preference import UIPreferenceRequest, UIPreferenceOut
from services.ui_preference_service import UIPreferenceService
from common import success

router = APIRouter()


@router.get("/user/preferences", response_model=UIPreferenceOut)
async def get_preferences(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的 UI 偏好设置（主题和字体大小）"""
    prefs = await UIPreferenceService.get_preferences(db, user.id)
    if not prefs:
        raise HTTPException(status_code=404, detail="用户不存在")
    return prefs


@router.patch("/user/preferences", response_model=UIPreferenceOut)
async def update_preferences(
    data: UIPreferenceRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新当前用户的 UI 偏好设置"""
    try:
        prefs = await UIPreferenceService.update_preferences(
            db,
            user.id,
            theme=data.theme,
            font_size=data.font_size,
        )
        if not prefs:
            raise HTTPException(status_code=404, detail="用户不存在")
        return prefs
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")
