"""
全局异常处理器 —— 框架占位，按注释实现。

【内容】
- @app.exception_handler(LunarisError)   → 返回统一错误响应
- @app.exception_handler(HTTPException)  → FastAPI 自带异常转换
- @app.exception_handler(Exception)      → 兜底 500（记录审计日志 + 脱敏）

【输出】统一格式（common/response.py）：
  { "code": <业务码>, "message": "...", "data": null, "timestamp": ... }
"""

# backend/exceptions/handlers.py
"""
全局异常处理器 —— 统一错误返回格式

处理三类异常：
1. AppException 和其子类 → 业务异常，记录日志 + 返回业务码
2. HTTPException → FastAPI/Starlette 异常，返回 HTTP 状态码
3. Exception → 未预期的异常（兜底 500）
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
import time

from core.error_handler import AppException
from config.logging_config import get_logger

logger = get_logger("handlers")


def register_exception_handlers(app: FastAPI):
    """
    注册全局异常处理器到 FastAPI 应用
    """

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        """
        处理业务异常（AppException 及其子类）

        特点：
        - 错误码在 1000-5999 之间
        - 记录详细日志（含堆栈、extra 字段）
        - 返回业务码而非 HTTP 状态码（便于前端区分）
        """
        exc.log()  # 记录错误日志

        logger.warning(
            f"业务异常: [{exc.code}] {exc.message}",
            extra={
                "code": exc.code,
                "http_status": exc.http_status,
                "path": request.url.path,
                "method": request.method,
                **exc.extra
            }
        )

        return JSONResponse(
            status_code=exc.http_status,
            content={
                "code": exc.code,
                "message": exc.message,
                "data": None,
                "timestamp": int(time.time())
            }
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """
        处理 HTTP 异常（401, 404, 400 等）

        这些异常来自 FastAPI/Starlette，使用 HTTP 状态码作为业务码。
        """
        logger.warning(
            f"HTTP异常: {exc.status_code} - {exc.detail}",
            extra={
                "code": exc.status_code,
                "path": request.url.path,
                "method": request.method,
            }
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.status_code,
                "message": exc.detail,
                "data": None,
                "timestamp": int(time.time())
            }
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """
        处理所有未捕获的异常（兜底 500）

        这表示代码中有 bug：本应被业务异常捕获的情况被遗漏，
        或者代码有真正的错误。记录完整堆栈便于调试。
        """
        logger.error(
            f"未处理的异常: {type(exc).__name__}: {str(exc)}",
            extra={
                "path": request.url.path,
                "method": request.method,
                "exception_type": type(exc).__name__,
            },
            exc_info=True
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": 500,
                "message": "服务器内部错误，请稍后重试",
                "data": None,
                "timestamp": int(time.time())
            }
        )