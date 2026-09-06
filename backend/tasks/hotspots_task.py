"""
热点缓存任务 —— 每小时拉取 RSS 热点，写进程内缓存。

【职责】
- refresh_hotspots()
  每小时执行：
  1. hotspot_client.fetch_hotspots()
  2. 写进程内缓存（模块级全局变量）
  3. 供 moments_task 与对话上下文引用

【说明】
- 缓存是进程内存实现：重启即清空；多实例/持久化后续接 Redis。
- 拉取失败保留上一批缓存（不清空），避免热点短暂断档。
"""
from datetime import datetime
from typing import List

from clients.hotspot_client import Hotspot, get_hotspot_client

# 进程内热点缓存（最近一次成功拉取的结果）
_hotspot_cache: List[Hotspot] = []
_last_refresh: datetime | None = None


def get_hotspots(limit: int = 10) -> List[Hotspot]:
    """读取当前热点缓存（供朋友圈文案 / 对话上下文引用）。"""
    return _hotspot_cache[:limit]


def get_last_refresh() -> datetime | None:
    """上次成功刷新时间（供诊断）。"""
    return _last_refresh


async def refresh_hotspots() -> List[Hotspot]:
    """刷新热点缓存。失败时保留旧缓存并返回旧值。"""
    global _hotspot_cache, _last_refresh
    try:
        hotspots = await get_hotspot_client().fetch_hotspots()
    except Exception as e:
        print(f"⚠️ 热点刷新失败: {e}")
        return _hotspot_cache

    if hotspots:
        _hotspot_cache = hotspots
        _last_refresh = datetime.now()
        print(f"🔥 热点已刷新: {len(hotspots)} 条，最近更新 {_last_refresh}")
    return _hotspot_cache
