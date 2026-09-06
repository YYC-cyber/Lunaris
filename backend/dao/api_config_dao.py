# backend/dao/api_config_dao.py
"""ApiConfigDAO —— 用户 API 配置数据访问（BYOK）。"""
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dao.base import BaseDAO
from models.user_api_config import UserApiConfig


class ApiConfigDAO(BaseDAO[UserApiConfig]):
    model = UserApiConfig

    @classmethod
    async def get_by_user_service(
        cls, db: AsyncSession, user_id: uuid.UUID, service: str
    ) -> Optional[UserApiConfig]:
        return (
            await db.execute(
                select(UserApiConfig).where(
                    UserApiConfig.user_id == user_id,
                    UserApiConfig.service == service,
                )
            )
        ).scalar_one_or_none()

    @classmethod
    async def list_by_user(cls, db: AsyncSession, user_id: uuid.UUID) -> list:
        return list(
            (
                await db.execute(
                    select(UserApiConfig).where(UserApiConfig.user_id == user_id)
                )
            ).scalars().all()
        )
