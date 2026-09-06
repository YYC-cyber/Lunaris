# controllers 包：路由处理器（HTTP / WebSocket 接口层）
#
# 【职责】
# - 每个 controller 一个 APIRouter，定义端点
# - 只做：参数校验（Pydantic）→ 调 service → 统一响应包装
#   （不写业务逻辑，不直接碰 DB）
# - main.py 统一挂载：app.include_router(..., prefix="/api")
# 【约定】函数命名即端点语义；鉴权依赖用 Depends(get_current_user)
