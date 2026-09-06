"""
业务异常基类 —— 框架占位，按注释实现。

【内容】
- class LunarisError(Exception):
    def __init__(self, code: int, message: str, http_status: int = 400)
  # code: 业务错误码（供前端区分），http_status: HTTP 状态码
- 预留错误码段：
  1000-1999 通用（参数错误、资源不存在）
  2000-2999 认证（未登录、token 失效、账号禁用）
  3000-3999 聊天/角色
  4000-4999 内容安全（敏感词命中、危机触发）
  5000-5999 外部服务（LLM/TTS/图片 超时）
"""

