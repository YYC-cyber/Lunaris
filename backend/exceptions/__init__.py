# exceptions 包：全局异常体系
#
# 【职责】
# - core/error_handler.py   业务异常定义（1000-5999）+ 详细日志记录
# - handlers.py             全局异常处理器 → 统一 JSON 响应
#
# 【约定】业务层抛自定义异常；controllers 不 try，由 handlers 统一捕获

from .handlers import register_exception_handlers
from core.error_handler import (
    AppException,
    # 通用异常 (1000-1999)
    ValidationException,
    NotFoundException,
    PermissionDeniedException,
    ConflictException,
    # 认证异常 (2000-2999)
    AuthenticationException,
    InvalidTokenException,
    AccountDisabledException,
    # 业务逻辑异常 (3000-3999)
    ChatException,
    MomentException,
    FriendshipException,
    GroupException,
    # 内容安全异常 (4000-4999)
    ContentSecurityException,
    SensitiveWordException,
    CrisisDetectedException,
    AppealException,
    # 外部服务异常 (5000-5999)
    ExternalServiceException,
    LLMException,
    TTSException,
    DatabaseException,
)

__all__ = [
    "register_exception_handlers",
    "AppException",
    "ValidationException",
    "NotFoundException",
    "PermissionDeniedException",
    "ConflictException",
    "AuthenticationException",
    "InvalidTokenException",
    "AccountDisabledException",
    "ChatException",
    "MomentException",
    "FriendshipException",
    "GroupException",
    "ContentSecurityException",
    "SensitiveWordException",
    "CrisisDetectedException",
    "AppealException",
    "ExternalServiceException",
    "LLMException",
    "TTSException",
    "DatabaseException",
]