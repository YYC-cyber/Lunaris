"""
统一的业务异常体系 —— 带有错误码、日志记录、HTTP 状态码映射

【错误码段】
- 1000-1999: 通用（参数错误、资源不存在、权限不足）
- 2000-2999: 认证（未登录、token 失效、账号禁用）
- 3000-3999: 业务逻辑（聊天、角色、朋友圈）
- 4000-4999: 内容安全（敏感词、危机检测、申诉）
- 5000-5999: 外部服务（LLM、TTS、图片生成超时）
"""
from typing import Optional, Dict, Any
from fastapi import status
from config.logging_config import get_logger

logger = get_logger("errors")


class AppException(Exception):
    """应用层基础异常 —— 所有业务异常的父类"""

    def __init__(
        self,
        code: int,
        message: str,
        http_status: int = status.HTTP_400_BAD_REQUEST,
        detail: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ):
        """
        Args:
            code: 业务错误码（供前端区分）
            message: 用户可见的错误消息
            http_status: HTTP 状态码
            detail: 内部调试信息（仅记录日志，不返回给前端）
            extra: 额外的日志字段（如 user_id, resource_id）
        """
        self.code = code
        self.message = message
        self.http_status = http_status
        self.detail = detail or message
        self.extra = extra or {}
        super().__init__(self.message)

    def log(self):
        """记录错误日志"""
        log_context = {"code": self.code, **self.extra}
        logger.error(f"{self.message} (detail: {self.detail})", extra=log_context, exc_info=True)


# ============================================================
# 通用异常 (1000-1999)
# ============================================================


class ValidationException(AppException):
    """参数验证失败"""

    def __init__(self, message: str, detail: Optional[str] = None, extra: Optional[Dict] = None):
        super().__init__(
            code=1001,
            message=message,
            http_status=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            extra=extra,
        )


class NotFoundException(AppException):
    """资源不存在"""

    def __init__(self, resource: str, resource_id: Any = None, extra: Optional[Dict] = None):
        message = f"{resource} 不存在"
        if resource_id:
            message += f"（ID: {resource_id}）"
        detail = f"Requested {resource} not found"
        super().__init__(
            code=1002,
            message=message,
            http_status=status.HTTP_404_NOT_FOUND,
            detail=detail,
            extra=extra or {"resource": resource, "resource_id": resource_id},
        )


class PermissionDeniedException(AppException):
    """权限不足"""

    def __init__(self, action: str = "此操作", reason: Optional[str] = None, extra: Optional[Dict] = None):
        message = f"权限不足，无法执行 {action}"
        if reason:
            message += f"（{reason}）"
        super().__init__(
            code=1003,
            message=message,
            http_status=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied for action: {action}",
            extra=extra or {"action": action},
        )


class ConflictException(AppException):
    """资源冲突（如重复、状态不匹配）"""

    def __init__(self, message: str, detail: Optional[str] = None, extra: Optional[Dict] = None):
        super().__init__(
            code=1004,
            message=message,
            http_status=status.HTTP_409_CONFLICT,
            detail=detail,
            extra=extra,
        )


# ============================================================
# 认证异常 (2000-2999)
# ============================================================


class AuthenticationException(AppException):
    """认证失败（未登录或无效凭证）"""

    def __init__(self, reason: str = "未登录", detail: Optional[str] = None, extra: Optional[Dict] = None):
        super().__init__(
            code=2001,
            message=reason,
            http_status=status.HTTP_401_UNAUTHORIZED,
            detail=detail or f"Authentication failed: {reason}",
            extra=extra or {"reason": reason},
        )


class InvalidTokenException(AppException):
    """Token 无效或已过期"""

    def __init__(self, reason: str = "Token 无效或已过期", detail: Optional[str] = None, extra: Optional[Dict] = None):
        super().__init__(
            code=2002,
            message=reason,
            http_status=status.HTTP_401_UNAUTHORIZED,
            detail=detail or f"Invalid or expired token: {reason}",
            extra=extra or {"reason": reason},
        )


class AccountDisabledException(AppException):
    """账户被禁用或删除"""

    def __init__(self, reason: str = "账户已禁用", extra: Optional[Dict] = None):
        super().__init__(
            code=2003,
            message=reason,
            http_status=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled or deleted",
            extra=extra or {"reason": reason},
        )


# ============================================================
# 业务逻辑异常 (3000-3999)
# ============================================================


class ChatException(AppException):
    """聊天相关异常"""

    def __init__(self, message: str, detail: Optional[str] = None, extra: Optional[Dict] = None):
        super().__init__(
            code=3001,
            message=message,
            http_status=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            extra=extra,
        )


class MomentException(AppException):
    """朋友圈相关异常"""

    def __init__(self, message: str, detail: Optional[str] = None, extra: Optional[Dict] = None):
        super().__init__(
            code=3002,
            message=message,
            http_status=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            extra=extra,
        )


class FriendshipException(AppException):
    """好友关系异常"""

    def __init__(self, message: str, detail: Optional[str] = None, extra: Optional[Dict] = None):
        super().__init__(
            code=3003,
            message=message,
            http_status=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            extra=extra,
        )


class GroupException(AppException):
    """群聊相关异常"""

    def __init__(self, message: str, detail: Optional[str] = None, extra: Optional[Dict] = None):
        super().__init__(
            code=3004,
            message=message,
            http_status=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            extra=extra,
        )


# ============================================================
# 内容安全异常 (4000-4999)
# ============================================================


class ContentSecurityException(AppException):
    """内容安全异常"""

    def __init__(self, message: str, detail: Optional[str] = None, extra: Optional[Dict] = None):
        super().__init__(
            code=4001,
            message=message,
            http_status=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            extra=extra,
        )


class SensitiveWordException(AppException):
    """敏感词检测失败"""

    def __init__(self, reason: str = "内容包含敏感词", extra: Optional[Dict] = None):
        super().__init__(
            code=4002,
            message=reason,
            http_status=status.HTTP_400_BAD_REQUEST,
            detail="Content contains sensitive words",
            extra=extra or {"reason": reason},
        )


class CrisisDetectedException(AppException):
    """危机信号检测"""

    def __init__(self, severity: str = "medium", detail: Optional[str] = None, extra: Optional[Dict] = None):
        message = "检测到可能的危机信号，已报告给守护者"
        super().__init__(
            code=4003,
            message=message,
            http_status=status.HTTP_400_BAD_REQUEST,
            detail=detail or f"Crisis detected with severity: {severity}",
            extra=extra or {"severity": severity},
        )


class AppealException(AppException):
    """申诉相关异常"""

    def __init__(self, message: str, detail: Optional[str] = None, extra: Optional[Dict] = None):
        super().__init__(
            code=4004,
            message=message,
            http_status=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            extra=extra,
        )


# ============================================================
# 外部服务异常 (5000-5999)
# ============================================================


class ExternalServiceException(AppException):
    """外部服务调用失败"""

    def __init__(
        self,
        service: str,
        message: str = "外部服务调用失败",
        detail: Optional[str] = None,
        extra: Optional[Dict] = None,
    ):
        full_message = f"{message}（{service}）"
        super().__init__(
            code=5001,
            message=full_message,
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail or f"External service {service} failed",
            extra=extra or {"service": service},
        )


class LLMException(AppException):
    """LLM 调用异常（超时、限流、错误）"""

    def __init__(self, reason: str = "LLM 调用失败", detail: Optional[str] = None, extra: Optional[Dict] = None):
        super().__init__(
            code=5002,
            message=f"AI 生成失败，{reason}，请稍后重试",
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail or f"LLM error: {reason}",
            extra=extra or {"reason": reason},
        )


class TTSException(AppException):
    """语音合成异常"""

    def __init__(self, reason: str = "语音生成失败", detail: Optional[str] = None, extra: Optional[Dict] = None):
        super().__init__(
            code=5003,
            message=f"语音生成失败，{reason}，请稍后重试",
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail or f"TTS error: {reason}",
            extra=extra or {"reason": reason},
        )


class DatabaseException(AppException):
    """数据库操作异常"""

    def __init__(self, message: str = "数据库操作失败", detail: Optional[str] = None, extra: Optional[Dict] = None):
        super().__init__(
            code=5004,
            message=message,
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail or "Database operation failed",
            extra=extra,
        )
