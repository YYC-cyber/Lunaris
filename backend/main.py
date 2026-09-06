# backend/main.py
"""
Lunaris 后端应用入口（FastAPI）
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
import time
import logging

from config.database import engine
from config.settings import get_settings
from config.logging_config import setup_logging, get_logger

# 初始化日志系统（必须在最前面）
setup_logging()

# 加载配置
settings = get_settings()
logger = get_logger("main")


# ---- 生命周期管理 ----
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭时的生命周期管理"""
    # ===== 启动阶段 =====
    logger.info("🚀 Lunaris 后端正在启动...")

    # 测试数据库连接
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("✅ 数据库连接成功！")
    except Exception as e:
        logger.error(f"❌ 数据库连接失败: {e}")
        raise e

    # 启动定时任务调度器（朋友圈 / 热点缓存 / 危机日报）
    from tasks.scheduler import start_scheduler
    start_scheduler()

    # P1-04: 启动 WebSocket 连接监控任务（心跳超时检测）
    import asyncio
    from ws.connection_manager import get_connection_manager
    manager = get_connection_manager()
    monitor_task = asyncio.create_task(manager.monitor_stale_connections(idle_timeout_seconds=90, check_interval_seconds=10))
    app.state.monitor_task = monitor_task
    logger.info("✅ WebSocket 连接监控任务已启动")

    logger.info("✅ Lunaris 后端启动完成！")

    yield  # 服务运行期间

    # ===== 关闭阶段 =====
    logger.info("🛑 Lunaris 后端正在关闭...")

    # 停止 WebSocket 连接监控任务
    if hasattr(app.state, 'monitor_task'):
        app.state.monitor_task.cancel()
        try:
            await app.state.monitor_task
        except asyncio.CancelledError:
            pass
        logger.info("✅ WebSocket 连接监控任务已停止")

    # 关闭定时任务调度器
    from tasks.scheduler import shutdown_scheduler
    shutdown_scheduler()

    await engine.dispose()
    logger.info("✅ 数据库连接池已关闭")


# ---- 创建 FastAPI 应用 ----
def create_app() -> FastAPI:
    app = FastAPI(
        title="Lunaris API",
        version="1.0.0",
        description="Lunaris AI 虚拟伴侣后端服务",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # ---- CORS 跨域中间件 ----
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---- 限流中间件（防滥用；在鉴权内层，可读 user_id）----
    from middleware.rate_limit import RateLimitMiddleware
    app.add_middleware(RateLimitMiddleware)

    # ---- 统一 JWT 鉴权中间件（白名单外的请求校验 Authorization）----
    from middleware.auth_middleware import AuthMiddleware
    app.add_middleware(AuthMiddleware)

    # ---- 静态音频（TTS 输出，/static/tts/xxx.mp3）----
    tts_dir = Path(__file__).resolve().parent / "data" / "tts"
    tts_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static/tts", StaticFiles(directory=tts_dir), name="tts")

    # ---- 静态上传文件（用户图片，/static/uploads/xxx.jpg）----
    uploads_dir = Path("/tmp/lunaris_uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static/uploads", StaticFiles(directory=uploads_dir), name="uploads")

    # ---- 全局异常处理 ----
    from exceptions import register_exception_handlers
    register_exception_handlers(app)

    # ---- 基础路由（健康检查） ----
    @app.get("/")
    async def root():
        return {
            "message": "Welcome to Lunaris API",
            "version": "1.0.0",
            "status": "running"
        }

    @app.get("/health")
    async def health_check():
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return {"status": "healthy", "database": "connected"}
        except Exception as e:
            return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

    # ---- 业务路由 ----
    from controllers import (
        auth_controller, soul_controller, chat_controller, moment_controller,
        friend_controller, settings_controller, admin_controller, conversation_controller,
        voice_controller, sticker_controller, ws_controller,
        upload_controller, group_controller, user_data_controller, report_controller,
        appeal_controller, sensitive_word_controller, crisis_escalation_controller,
        block_controller, admin_batch_controller, admin_export_controller,
        ui_preference_controller, search_controller, user_status_controller, friend_search_controller,
        group_mute_controller, group_permission_controller, group_announcement_controller,
        monitor_controller, knowledge_controller,
    )
    app.include_router(auth_controller.router, prefix="/api/auth", tags=["认证"])
    app.include_router(user_data_controller.router, tags=["用户数据"])  # 数据导出、删除、更新
    app.include_router(report_controller.router, tags=["举报管理"])  # 用户举报、管理员审核
    app.include_router(block_controller.router, tags=["屏蔽管理"])  # 用户屏蔽、黑名单
    app.include_router(appeal_controller.router, tags=["申诉管理"])  # 用户申诉、管理员审核
    app.include_router(sensitive_word_controller.router, tags=["敏感词管理"])  # 敏感词管理
    app.include_router(crisis_escalation_controller.router, tags=["危机升级"])  # 危机升级管理
    app.include_router(monitor_controller.router, tags=["监控"])  # #8: 系统监控
    app.include_router(group_mute_controller.router, prefix="/api", tags=["群聊"])  # P2-02: 群禁言
    app.include_router(group_permission_controller.router, prefix="/api", tags=["群聊"])  # P2-03: 群权限
    app.include_router(group_announcement_controller.router, prefix="/api", tags=["群聊"])  # P2-15: 群公告
    app.include_router(soul_controller.router, prefix="/api/souls", tags=["角色"])
    app.include_router(chat_controller.router, prefix="/v1/chat", tags=["聊天"])   # 注意：是 /v1/chat，不是 /v1
    app.include_router(moment_controller.router, prefix="/api/moments", tags=["朋友圈"])
    app.include_router(friend_controller.router, prefix="/api/friends", tags=["好友"])
    app.include_router(conversation_controller.router, prefix="/api/conversations", tags=["会话"])
    app.include_router(settings_controller.router, prefix="/api/settings", tags=["设置"])
    app.include_router(admin_controller.router, prefix="/api/admin", tags=["后台管理"])
    app.include_router(admin_batch_controller.router, prefix="/api/admin", tags=["后台管理"])
    app.include_router(admin_export_controller.router, prefix="/api/admin/export", tags=["后台管理"])
    app.include_router(voice_controller.router, prefix="/api/voice", tags=["语音"])
    app.include_router(sticker_controller.router, prefix="/api/stickers", tags=["表情包"])
    app.include_router(upload_controller.router, prefix="/api/upload", tags=["上传"])
    app.include_router(search_controller.router, prefix="/api/search", tags=["搜索"])  # P2-01: 消息搜索
    app.include_router(user_status_controller.router, prefix="/api/users", tags=["用户"])  # P2-05: 在线状态
    app.include_router(friend_search_controller.router, prefix="/api/friends", tags=["好友"])  # P2-07: 用户搜索
    app.include_router(ui_preference_controller.router, tags=["UI偏好"])  # P2-10/11: UI 偏好设置
    app.include_router(group_controller.router, prefix="/api", tags=["群聊"])
    app.include_router(knowledge_controller.router, prefix="/api/knowledge", tags=["知识库"])  # RAG 知识库
    app.include_router(ws_controller.router, prefix="/api", tags=["WebSocket"])   # → /api/ws
    return app


# ---- 导出 app 实例（供 uvicorn/gunicorn 使用） ----
app = create_app()


# ---- 方便调试直接运行 ----
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
