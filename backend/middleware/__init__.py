# middleware 包：FastAPI 中间件
#
# 【职责】
# - auth_middleware.py JWT 鉴权（注入 request.state.user_id）+ get_current_user 依赖
# - cors.py            CORS 白名单（当前在 main.py 直接装配）
# - rate_limit.py      请求限流（TODO）
# - logging_middleware.py  请求日志 + request_id（TODO）
#
# 【顺序】由 main.py 的 create_app() 装配

from .auth_middleware import AuthMiddleware, get_current_user

__all__ = ["AuthMiddleware", "get_current_user"]
