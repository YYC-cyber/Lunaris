# backend/controllers/monitor_controller.py
"""系统监控 —— 运行指标、进程健康、数据库状态（任务 #8）。"""
import asyncio
import os
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from config.settings import get_settings
from ws.connection_manager import get_connection_manager

router = APIRouter()

# 应用启动时间（用于计算 uptime）
START_TIME = time.time()


@router.get("/metrics")
async def metrics(
    db: AsyncSession = Depends(get_db),
):
    """获取系统运行指标。

    返回：内存、进程、数据库连接、WebSocket 在线数、请求速率等。
    """
    import resource
    import psutil  # 可选依赖，失败时降级

    uptime_seconds = int(time.time() - START_TIME)
    uptime_h = uptime_seconds // 3600
    uptime_m = (uptime_seconds % 3600) // 60

    # 内存（psutil 可选）
    memory_info = {}
    try:
        import psutil as _ps
        mem = _ps.virtual_memory()
        memory_info = {
            "total_mb": round(mem.total / 1024 / 1024),
            "used_mb": round(mem.used / 1024 / 1024),
            "percent": mem.percent,
        }
    except ImportError:
        # 无 psutil 时用 resource 模块
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        memory_info = {"rss_mb": round(rss / 1024)}

    # 进程数
    proc_count = len(os.listdir('/proc')) if os.path.isdir('/proc') else None

    # WebSocket 在线连接数
    try:
        cm = get_connection_manager()
        online = len(cm._connections) if hasattr(cm, '_connections') else cm.get_online_count()
    except Exception:
        online = None

    return {
        "app": "lunaris-backend",
        "version": "1.1",
        "uptime_seconds": uptime_seconds,
        "uptime_human": f"{uptime_h}h {uptime_m}m",
        "started_at": datetime.fromtimestamp(START_TIME, tz=timezone.utc).isoformat(),
        "memory": memory_info,
        "processes": proc_count,
        "ws_online": online,
        "python_version": os.sys.version.split()[0],
        "pid": os.getpid(),
    }


@router.get("/health/detail")
async def health_detail(
    db: AsyncSession = Depends(get_db),
):
    """详细健康检查：数据库 + 关键依赖状态。"""
    checks = {}

    # 数据库
    try:
        async with db.begin():
            await db.execute(text("SELECT 1"))
        checks["database"] = {"status": "ok"}
    except Exception as e:
        checks["database"] = {"status": "error", "detail": str(e)}

    # 数据库表数量
    try:
        r = await db.execute(text(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'"
        ))
        checks["tables"] = {"status": "ok", "count": r.scalar()}
    except Exception as e:
        checks["tables"] = {"status": "error", "detail": str(e)}

    overall = "healthy" if all(c.get("status") == "ok" for c in checks.values()) else "degraded"
    return {"status": overall, "checks": checks, "timestamp": datetime.now(timezone.utc).isoformat()}
