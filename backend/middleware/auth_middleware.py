# backend/middleware/auth_middleware.py
"""统一 JWT 鉴权中间件 + get_current_user 依赖。

用纯 ASGI 中间件实现（不用 BaseHTTPMiddleware）——因为 BaseHTTPMiddleware 在
dispatch 里设置的 request.state 不会传播到路由 handler，纯 ASGI 直接写
scope["state"] 才能可靠地让 handler 通过 request.state.user_id 读取。

【职责】
- 白名单路径（注册/登录/WS/健康检查等）直接放行
- 其余 HTTP 请求校验 Authorization: Bearer <token>，把 user_id 注入 scope["state"]
- 未带 / 无效 token → 401（统一响应格式）
- get_current_user 依赖：从 request.state.user_id 懒加载 User
"""
import json
import time
import uuid

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from config.settings import get_settings
from models.user import User
from services.auth_service import AuthService

settings = get_settings()


def is_admin_user(user: User) -> bool:
    """Return the canonical administrator status used by all admin APIs.

    仅凭 user.is_admin 数据库标记判定，不再对用户名（admin/luna 等）硬编码放行。
    admin 与 luna 的管理后台访问完全交由 admin-react 前端，主应用不展示管理入口。
    """
    return bool(user.is_admin)

# 无需登录的公共路径（前缀匹配）
PUBLIC_PATHS = [
    "/api/auth/register",
    "/api/auth/login",
    "/api/ws",  # WS 握手用 query token 单独校验（见 ws_controller）
    "/health",
    "/",
    "/static",  # TTS 音频文件（/static/tts/xxx.mp3）
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
]


def _unauthorized_body(message: str) -> bytes:
    return json.dumps(
        {"code": 401, "message": message, "data": None, "timestamp": int(time.time())},
        ensure_ascii=False,
    ).encode("utf-8")


class AuthMiddleware:
    """纯 ASGI 中间件：HTTP 请求校验 JWT，注入 scope["state"]["user_id"]。"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # 非 HTTP（WebSocket / lifespan）直接放行（WS 由 ws_controller 单独校验）
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # CORS 预检放行
        if scope.get("method") == "OPTIONS":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        # 白名单放行："/" 只做精确匹配（否则 path.startswith("/") 会匹配所有路径）
        if any(path == p or (p != "/" and path.startswith(p)) for p in PUBLIC_PATHS):
            await self.app(scope, receive, send)
            return

        # 校验 JWT
        headers = {k.decode("utf-8").lower(): v.decode("utf-8") for k, v in scope.get("headers", [])}
        auth = headers.get("authorization", "")
        if not auth.startswith("Bearer "):
            await self._reject(send, "未提供有效凭证")
            return
        token = auth[7:]
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
            user_id = payload.get("sub")
            if not user_id:
                await self._reject(send, "凭证无效或已过期")
                return
        except JWTError:
            await self._reject(send, "凭证无效或已过期")
            return

        # 注入 user_id 到 scope state（request.state.user_id 可读）
        scope.setdefault("state", {})["user_id"] = user_id
        await self.app(scope, receive, send)

    async def _reject(self, send, message: str) -> None:
        body = _unauthorized_body(message)
        await send({
            "type": "http.response.start",
            "status": 401,
            "headers": [(b"content-type", b"application/json; charset=utf-8")],
        })
        await send({"type": "http.response.body", "body": body})


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """从 Authorization 头解析当前用户（供 controller 依赖注入）。

    不依赖中间件注入的 request.state（Starlette 版本间传递不稳定），
    直接解码 Authorization 头，与中间件门禁双保险。
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供有效凭证")
    token = auth[7:]
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="凭证无效或已过期")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="凭证无效或已过期")
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="凭证无效")

    user = await AuthService.get_user_by_id(db, uid)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return user
