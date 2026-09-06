# core 包：核心引擎
#
# 【职责】
# - agent.py     AI 对话编排（多轮工具调用 + 流式）
# - memory.py    长期记忆引擎（提取/分类/摘要/注入）
# - security.py  内容安全三层防御（敏感词 + llm-guard + 审计联动）
# - crisis.py    危机干预（识别 + 话术模板 + 事件记录 + 记忆隔离）
# - audit_log.py 审计日志写入
#
# 【说明】core 只依赖 clients / dao，不依赖 controllers / middleware
