"""
认证 DTO —— 框架占位，按注释实现。

【内容】
- RegisterIn:   username(str, 长度校验), password(str, 强度校验),
                gender(Literal['male','female']), birthday(date 可选)
- LoginIn:      username, password
- TokenOut:     user_id, token(str), default_soul(可选 SoulOut)   # 登录返回
- UserOut:      user_id, username, gender, nickname, avatar_url, created_at

【说明】
- TokenOut 的 default_soul 用于登录后直接定位默认伴侣
- 密码字段永不回显，出参模型不要包含 password_hash
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime
import uuid

# ---- 注册请求 ----
class RegisterIn(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=100, description="密码")
    gender: str = Field(..., pattern="^(male|female)$", description="性别: male/female")
    birthday: Optional[datetime] = Field(None, description="出生日期（用于年龄验证）")
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    guardian_email: Optional[str] = Field(
        None,
        description="监护人邮箱（14-18岁用户需填写）"
    )

# ---- 登录请求 ----
class LoginIn(BaseModel):
    username: str
    password: str

# ---- 登录/注册响应 ----
class TokenOut(BaseModel):
    user_id: uuid.UUID
    username: str
    gender: str
    token: str
    expires_in: int  # 秒
    theme: Optional[str] = None  # P2-10: UI 偏好
    font_size: Optional[str] = None  # P2-10: UI 偏好

# ---- 用户信息（用于 /me） ----
class UserOut(BaseModel):
    id: uuid.UUID
    username: str
    lunaris_id: Optional[str] = None
    gender: str
    api_granted_until: Optional[datetime] = None
    nickname: Optional[str]
    avatar_url: Optional[str]
    birthday: Optional[datetime]
    is_active: bool
    is_admin: bool = False
    created_at: datetime
    last_login_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)  # 允许从 ORM User 直接序列化


# ---- 修改密码请求 ----
class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., description="当前密码")
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="新密码（至少8字符）"
    )
