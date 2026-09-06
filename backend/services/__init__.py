# services 包：业务逻辑层
#
# 【职责】
# - 承载所有业务规则（认证、聊天编排、朋友圈、社区、知识库、配对、实时通知）
# - 依赖关系：services → dao / core / clients / ws
# - services 之间可互相调用（如 chat_service 调 notify_service）
# 【约定】每个 service 用类 + 模块级单例实例（如 auth_service = AuthService()）
#         方法全异步；事务边界在本层用 async with session 控制
