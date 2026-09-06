"""
统一响应格式 —— 框架占位，按注释实现。

【内容】
- success(data=None, message="success") -> JSONResponse
  { "code": 0, "message": "success", "data": data, "timestamp": ... }
- error(code, message, http_status=400) -> JSONResponse
  { "code": code, "message": message, "data": null, "timestamp": ... }

【说明】
- 所有 controller 返回值统一走 success()；异常由 handlers.py 走 error()
- timestamp 用秒级 Unix 时间戳
"""

# backend/common/response.py
"""
统一响应格式工具

所有 controller 统一使用这里的函数返回响应，保证前端收到的格式一致。
"""

import time
from typing import Any, Optional, TypeVar, Generic
from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一响应模型"""
    code: int = 0
    message: str = "success"
    data: Optional[T] = None
    timestamp: int = 0

    @classmethod
    def success(cls, data: Any = None, message: str = "success") -> "ApiResponse":
        """成功响应"""
        return cls(
            code=0,
            message=message,
            data=data,
            timestamp=int(time.time())
        )

    @classmethod
    def error(cls, code: int, message: str, data: Any = None) -> "ApiResponse":
        """错误响应"""
        return cls(
            code=code,
            message=message,
            data=data,
            timestamp=int(time.time())
        )


# 为了更便捷的使用，也可以直接定义函数风格的快捷方式

def success(data: Any = None, message: str = "success") -> dict:
    """返回成功响应字典"""
    return {
        "code": 0,
        "message": message,
        "data": data,
        "timestamp": int(time.time())
    }


def error(code: int, message: str, data: Any = None) -> dict:
    """返回错误响应字典"""
    return {
        "code": code,
        "message": message,
        "data": data,
        "timestamp": int(time.time())
    }