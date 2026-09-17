# backend/services/ui_preference_service.py
"""UI 偏好设置服务"""
import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from dao.user_dao import UserDAO


class UIPreferenceService:
    VALID_THEMES = {"light", "dark"}
    VALID_FONT_SIZES = {"small", "normal", "large", "xlarge"}

    @staticmethod
    async def get_preferences(db: AsyncSession, user_id: uuid.UUID) -> dict:
        """获取用户的 UI 偏好设置"""
        user = await UserDAO.get(db, user_id)
        if not user:
            return None
        return {
            "theme": user.theme,
            "font_size": user.font_size,
        }

    @staticmethod
    async def update_preferences(
        db: AsyncSession,
        user_id: uuid.UUID,
        theme: Optional[str] = None,
        font_size: Optional[str] = None,
    ) -> Optional[dict]:
        """更新用户的 UI 偏好设置"""
        # 验证主题
        if theme and theme not in UIPreferenceService.VALID_THEMES:
            raise ValueError(f"主题无效：{theme}。必须是 light 或 dark。")

        # 验证字体大小
        if font_size and font_size not in UIPreferenceService.VALID_FONT_SIZES:
            raise ValueError(f"字体大小无效：{font_size}。必须是 small/normal/large/xlarge 之一。")

        user = await UserDAO.get(db, user_id)
        if not user:
            return None

        if theme:
            user.theme = theme
        if font_size:
            user.font_size = font_size

        db.add(user)
        await db.commit()
        await db.refresh(user)

        return {
            "theme": user.theme,
            "font_size": user.font_size,
        }
