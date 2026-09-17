# backend/schemas/ui_preference.py
"""UI 偏好设置 DTO（Data Transfer Objects）"""
from pydantic import BaseModel, Field


class UIPreferenceRequest(BaseModel):
    """更新 UI 偏好设置请求"""
    theme: str = Field(None, pattern="^(light|dark)$", description="主题：light/dark")
    font_size: str = Field(None, pattern="^(small|normal|large|xlarge)$", description="字体大小：small/normal/large/xlarge")

    class Config:
        # 允许字段为 None（可选更新）
        extra = "ignore"


class UIPreferenceOut(BaseModel):
    """UI 偏好设置响应"""
    theme: str
    font_size: str

    class Config:
        from_attributes = True
