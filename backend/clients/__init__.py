# clients 包：外部 API 客户端
#
# 【职责】
# - 封装所有第三方调用（LLM / Whisper / TTS / 图片 / 热点）
# - 统一超时 / 重试 / 异常转业务异常
# 【约定】全部异步；只在 services / core 中使用
