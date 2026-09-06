"""
请求日志中间件 —— 框架占位，按注释实现。

【内容】
- 每个请求生成 request_id（UUID），存入 contextvar 贯穿链路
- 记录：method, path, status, 耗时 ms, user_id(若有), request_id
- 使用 loguru 输出结构化日志（backend/logs/）
- 错误响应体记录（方便排障，注意脱敏）

【说明】request_id 供 core/audit_log 复用，实现全链路追踪
"""
