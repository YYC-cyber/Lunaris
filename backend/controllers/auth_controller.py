"""
认证 HTTP 控制器 —— 接收请求，调用 AuthService，返回响应。

【职责】
- POST /api/auth/register  → 接收注册请求 → 调用 AuthService.register_user → 返回 Token
- POST /api/auth/login     → 接收登录请求 → 调用 AuthService.login_user → 返回 Token
- GET  /api/auth/me        → 获取当前用户信息（需要 JWT 鉴权，暂占位）

【调用链】
HTTP请求 → 控制器(本文件) → 服务层(AuthService) → DAO层(最终操作数据库)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from common import success
from config.database import get_db
from config.settings import get_settings
from middleware.auth_middleware import get_current_user
from models.user import User
from schemas.auth import RegisterIn, LoginIn, TokenOut, UserOut, ChangePasswordRequest
from services.auth_service import AuthService

# 创建路由组，所有接口前缀为 /api/auth
router = APIRouter()
settings = get_settings()


@router.post("/register", response_model=TokenOut)
async def register(
    data: RegisterIn,
    db: AsyncSession = Depends(get_db),
):
    """
    用户注册接口（中国 PIPL 合规版本）

    流程：
    1. 验证出生日期和年龄（14 岁以下拒绝）
    2. 14-18 岁用户需要提供监护人邮箱
    3. 调用 AuthService.register_user 执行注册
    4. 如果用户名已被占用，返回 400 错误
    5. 注册成功 → 生成 JWT Token → 返回给前端

    PIPL 合规要点：
    - 第 35 条：儿童信息保护（14 岁以下拒绝）
    - 第 5 条：显示隐私政策
    """
    try:
        from services.auth_service import AgeVerificationError

        user = await AuthService.register_user(
            db=db,
            username=data.username,
            password=data.password,
            gender=data.gender,
            nickname=data.nickname,
            birthday=data.birthday,
            guardian_email=data.guardian_email,
        )
    except ValueError as e:
        # 用户名已被注册或其他业务错误
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        # 年龄验证或其他错误
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # 自动配对（AUTH-05）：注册成功即分配一位异性 AI 伴侣
    from services.matching_service import MatchingService
    from services.soul_service import SoulService
    try:
        friendship = await MatchingService.auto_match(db, user.id, user.gender)
        await db.commit()
        if friendship:
            # AI 开场白（SOUL-05）
            await SoulService.send_first_greeting(db, user.id, friendship.soul_id)
    except Exception as e:
        print(f"⚠️ 自动配对失败: {e}")

    # 生成 JWT Token
    token = AuthService.create_token(user.id)

    return TokenOut(
        user_id=user.id,
        username=user.username,
        gender=user.gender,
        token=token,
        expires_in=settings.JWT_EXPIRE_DAYS * 24 * 60 * 60,  # 转换为秒
        theme=user.theme,  # P2-10: UI 偏好
        font_size=user.font_size,  # P2-10: UI 偏好
    )


@router.post("/login", response_model=TokenOut)
async def login(
    data: LoginIn,
    db: AsyncSession = Depends(get_db),
):
    """
    用户登录接口

    流程：
    1. 接收用户名和密码
    2. 调用 AuthService.login_user 验证
    3. 用户名或密码错误 → 返回 401
    4. 验证通过 → 生成 JWT Token → 返回给前端
    """
    user = await AuthService.login_user(
        db=db,
        username=data.username,
        password=data.password,
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    token = AuthService.create_token(user.id)

    return TokenOut(
        user_id=user.id,
        username=user.username,
        gender=user.gender,
        token=token,
        expires_in=settings.JWT_EXPIRE_DAYS * 24 * 60 * 60,
    )


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    """获取当前用户信息（含 API 授权剩余天数）。统一响应格式。"""
    from common.helpers import remaining_days
    data = UserOut.model_validate(user).model_dump()
    data["remaining_days"] = remaining_days(user.api_granted_until)
    return success(data=data, message="获取用户信息成功")


@router.post("/logout")
async def logout(user: User = Depends(get_current_user)):
    """退出登录。JWT 无状态，登出由客户端丢弃 token；如需强制失效后续加黑名单/Redis。"""
    return {"success": True, "user_id": str(user.id)}


@router.post("/refresh", response_model=TokenOut)
async def refresh(user: User = Depends(get_current_user)):
    """刷新 Token：验证当前 token 有效后签发新 token。"""
    token = AuthService.create_token(user.id)
    return TokenOut(
        user_id=user.id,
        username=user.username,
        gender=user.gender,
        token=token,
        expires_in=settings.JWT_EXPIRE_DAYS * 24 * 60 * 60,
        theme=user.theme,  # P2-10: UI 偏好
        font_size=user.font_size,  # P2-10: UI 偏好
    )


@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改密码"""
    try:
        success = await AuthService.change_password(
            db,
            user,
            data.old_password,
            data.new_password,
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="当前密码错误",
            )
        return success(
            data={"success": True},
            message="密码已修改",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="修改密码失败，请稍后重试",
        )



@router.get("/verify-guardian")
async def verify_guardian(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    监护人验证端点 - 测试环境

    当监护人点击邮件中的验证链接时调用。
    生产环境应替换为真实邮件验证流程。

    Args:
        token: 验证令牌（来自邮件链接）

    Returns:
        验证结果和激活账户
    """
    from services.guardian_email_service import GuardianEmailService
    from dao.user_dao import UserDAO

    # 验证令牌
    verification_record = GuardianEmailService.verify_guardian_token(token)

    if not verification_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证链接已过期或无效。请联系我们重新生成。"
        )

    # 激活用户账户
    user = await UserDAO.get(db, verification_record["user_id"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    user.is_active = True
    await db.commit()

    return success(
        data={
            "user_id": str(user.id),
            "username": user.username,
            "message": "监护人确认成功！账户已激活，可以开始使用。"
        }
    )
