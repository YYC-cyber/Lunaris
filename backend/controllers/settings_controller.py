# backend/controllers/settings_controller.py
"""设置路由 —— 当前实现「API 配置」（BYOK，用户自带 Key）。"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from middleware.auth_middleware import get_current_user
from models.user import User
from services.api_config_service import SERVICES, ApiConfigService

router = APIRouter()


class ApiConfigIn(BaseModel):
    service: str
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None


@router.get("/api-config")
async def get_api_configs(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查看我的 API 配置（Key 只返回脱敏值）。"""
    configs = await ApiConfigService.get_all_configs(db, user.id)
    return {
        "data": {
            service: {
                "service": service,
                "api_key_masked": ApiConfigService.mask_key(c.api_key),
                "base_url": c.base_url,
                "model": c.model,
                "is_configured": bool(c.api_key),
            }
            for service, c in configs.items()
        }
    }


@router.put("/api-config")
async def update_api_config(
    data: ApiConfigIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """保存某服务的 API 配置（api_key 留空则保持原值）。"""
    try:
        config = await ApiConfigService.upsert_config(
            db, user.id, data.service, data.api_key, data.base_url, data.model
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {
        "success": True,
        "service": config.service,
        "api_key_masked": ApiConfigService.mask_key(config.api_key),
        "is_configured": bool(config.api_key),
    }


@router.post("/api-config/test")
async def test_api_config(
    data: ApiConfigIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """测试某服务连接（BYOK-05）。api_key 留空则用已保存的配置测。"""
    service = data.service
    if service not in SERVICES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"未知服务: {service}")

    # 若传了新 key 先用新的测，否则用已保存配置（resolve 会解密 + 回退平台 key）
    cfg = None
    if data.api_key:
        cfg = {"api_key": data.api_key, "base_url": data.base_url, "model": data.model}
    else:
        cfg = await ApiConfigService.resolve(db, user.id, service)
    if not cfg.get("api_key"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="未配置 API Key，无法测试")

    try:
        result = await ApiConfigService.test_connection(service, cfg)
        return {"success": True, "service": service, **result}
    except ValueError as e:
        return {"success": False, "service": service, "error": str(e)}
