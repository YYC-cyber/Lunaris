# backend/ws/connection_manager.py
"""WS 连接管理：连接注册表 + 推送 + 心跳 + 离线补发。

【方法】
- register / unregister          连接注册与注销
- push(user_id, event)           推送事件（在线直发 / 离线入队）
- get_online_count / get_all_online  统计

【说明】全局单例 get_connection_manager()；心跳协议见 schemas/ws.py
"""
import asyncio
import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from starlette.websockets import WebSocket

# 离线队列上限，防止无限膨胀
OFFLINE_QUEUE_LIMIT = 100


class ConnectionManager:
    def __init__(self) -> None:
        # 在线连接: user_id_str → list[WebSocket]（一人可多连接，多端同步）
        self.active_connections: Dict[str, List[WebSocket]] = defaultdict(list)
        # 离线队列: user_id_str → list[event_dict]（断线补发）
        self.offline_queues: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        # 保护注册表 / 离线队列的并发读写
        self._lock = asyncio.Lock()
        # P1-04: 最后 pong 时间戳（用于心跳超时检测）
        self.last_pong_at: Dict[str, datetime] = {}
        # P1-04: 连接打开时间（用于计算空闲时长）
        self.connection_opened_at: Dict[str, datetime] = {}

    # ---------- 连接注册 / 注销 ----------
    async def register(self, user_id: str, websocket: WebSocket) -> None:
        """注册连接；如有离线缓存则补发（补发不持锁，避免阻塞其它注册）。"""
        async with self._lock:
            self.active_connections[user_id].append(websocket)
            # P1-04: 记录连接打开时间和最后 pong 时间
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            self.connection_opened_at[user_id] = now
            self.last_pong_at[user_id] = now
            events = self.offline_queues.get(user_id, [])
            if events:
                self.offline_queues[user_id] = []
        if events:
            print(f"📦 补发 {len(events)} 条离线事件给用户 {user_id}")
            for event in events:
                await self._send(websocket, event)

    async def unregister(self, user_id: str, websocket: WebSocket) -> None:
        """注销连接；无剩余连接时移除该用户。"""
        async with self._lock:
            conns = self.active_connections.get(user_id, [])
            try:
                conns.remove(websocket)
            except ValueError:
                pass
            if not conns:
                self.active_connections.pop(user_id, None)
                # P1-04: 清除心跳相关的时间戳
                self.last_pong_at.pop(user_id, None)
                self.connection_opened_at.pop(user_id, None)

    # ---------- 推送 ----------
    async def push(
        self,
        user_id: str,
        event_type: str,
        event_id: str,
        data: Dict[str, Any],
    ) -> None:
        """推送事件给指定用户。

        - 在线：发送给该用户全部连接（多端同步）
        - 发送失败（连接已断）的连接会被清理
        - 全部连接失效或离线：写入离线队列，重连时补发
        """
        event = {
            "type": event_type,
            "id": event_id,
            "data": data,
            "ts": int(datetime.now(timezone.utc).timestamp()),
        }

        async with self._lock:
            connections = list(self.active_connections.get(user_id, []))
            if not connections:
                self._enqueue_offline(user_id, event)
                return

        # 在线发送（不持锁，避免慢连接阻塞其它推送）
        to_remove = [ws for ws in connections if not await self._send(ws, event)]
        if not to_remove:
            return

        async with self._lock:
            for ws in to_remove:
                try:
                    self.active_connections[user_id].remove(ws)
                except (KeyError, ValueError):
                    pass
            if not self.active_connections.get(user_id):
                self.active_connections.pop(user_id, None)
                self._enqueue_offline(user_id, event)

    def _enqueue_offline(self, user_id: str, event: Dict[str, Any]) -> None:
        """写入离线队列（限长）。调用方需已持有 _lock。"""
        q = self.offline_queues[user_id]
        q.append(event)
        if len(q) > OFFLINE_QUEUE_LIMIT:
            del q[: len(q) - OFFLINE_QUEUE_LIMIT]

    async def _send(self, websocket: WebSocket, event: Dict[str, Any]) -> bool:
        """发送单条消息，失败（连接已关）返回 False。"""
        try:
            # ensure_ascii=False：中文不发成 \uXXXX 转义
            await websocket.send_text(json.dumps(event, ensure_ascii=False))
            return True
        except Exception:
            return False

    # ---------- 统计 ----------
    def get_online_count(self, user_id: str) -> int:
        return len(self.active_connections.get(user_id, []))

    def get_all_online(self) -> List[str]:
        return list(self.active_connections.keys())

    # ---------- P1-04: 心跳管理 ----------
    async def handle_pong(self, user_id: str) -> None:
        """处理 pong 消息，更新最后 pong 时间戳。"""
        async with self._lock:
            self.last_pong_at[user_id] = datetime.now(timezone.utc).replace(tzinfo=None)

    async def monitor_stale_connections(self, idle_timeout_seconds: int = 90, check_interval_seconds: int = 10) -> None:
        """后台任务：监控并关闭超过空闲时限的连接。

        Args:
            idle_timeout_seconds: 连接空闲超时时长（秒），默认 90 秒
            check_interval_seconds: 检查间隔（秒），默认 10 秒
        """
        import asyncio

        while True:
            try:
                await asyncio.sleep(check_interval_seconds)

                now = datetime.now(timezone.utc).replace(tzinfo=None)
                stale_users = []

                async with self._lock:
                    for user_id, last_pong in list(self.last_pong_at.items()):
                        elapsed = (now - last_pong).total_seconds()
                        if elapsed > idle_timeout_seconds:
                            stale_users.append(user_id)

                # 关闭超时连接（不持锁，避免阻塞其它操作）
                for user_id in stale_users:
                    conns = self.active_connections.get(user_id, [])
                    for ws in conns:
                        try:
                            await ws.close(code=1000, reason="Connection idle timeout")
                        except Exception as e:
                            print(f"⚠️ 关闭超时连接失败 (user_id={user_id}): {e}")

                    # 清除该用户的连接和时间戳
                    async with self._lock:
                        self.active_connections.pop(user_id, None)
                        self.last_pong_at.pop(user_id, None)
                        self.connection_opened_at.pop(user_id, None)

                    if stale_users:
                        print(f"✅ 已关闭 {len(stale_users)} 个超时连接")

            except Exception as e:
                print(f"⚠️ 连接监控任务出错: {e}")
                # 继续监控，不中断


# 全局单例（进程内）
_manager: Optional[ConnectionManager] = None


def get_connection_manager() -> ConnectionManager:
    """获取全局单例。"""
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager
