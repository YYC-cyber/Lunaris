# tests 包：后端测试
#
# 【约定】
# - pytest + pytest-asyncio + httpx AsyncClient（ASGITransport）
# - 数据库用独立测试库或 SQLite 内存（注意 pgvector 向量类型兼容性，
#   建议测试环境也用 PostgreSQL 测试库）
# - 外部调用（LLM/TTS/图片）全部 mock
