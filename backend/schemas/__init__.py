# schemas 包：Pydantic DTO（请求体 / 响应体）
#
# 【职责】
# - 每个模块一个文件，定义入参校验模型与出参模型
# - 出参统一用 common/response.py 的 success(data=...) 包装
# - 命名约定：*In = 请求体，*Out = 响应体，*PageOut = 分页结果
