"""
认证异常 —— 框架占位，按注释实现。

【内容】继承 LunarisError 的专属异常：
- UnauthorizedError      # 未登录 / token 缺失（401）
- TokenExpiredError      # token 过期（401，前端触发 refresh）
- InvalidCredentialsError  # 用户名或密码错误（400）
- UsernameTakenError     # 用户名已存在（409）
- AccountDisabledError   # 账号被禁用（403）
"""
