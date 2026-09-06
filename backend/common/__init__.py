# common 包：通用工具
#
# 【职责】
# - constants.py   全局常量
# - enums.py       枚举类型
# - helpers.py     通用函数（时间戳/UUID/校验）
# - response.py    统一响应格式（所有接口出口）
#
# 【约定】无业务依赖，任何层都可导入

# backend/common/__init__.py
from .response import success, error, ApiResponse

__all__ = ["success", "error", "ApiResponse"]