"""
WebSocket 连接管理单元测试 —— 用 fake WebSocket 对象，无需真实网络。

覆盖：注册 / 在线推送 / 离线入队 / 重连补发 / 注销。
"""
import asyncio

from ws.connection_manager import ConnectionManager


class FakeWebSocket:
    def __init__(self):
        self.sent = []

    async def send_text(self, text):
        self.sent.append(text)


def test_register_and_push_online():
    async def _run():
        mgr = ConnectionManager()
        ws = FakeWebSocket()
        await mgr.register("u1", ws)
        assert mgr.get_online_count("u1") == 1

        await mgr.push("u1", "message", "e1", {"content": "hi"})
        assert len(ws.sent) == 1
        assert "e1" in ws.sent[0]
        assert "message" in ws.sent[0]
    asyncio.run(_run())


def test_push_offline_enqueues():
    async def _run():
        mgr = ConnectionManager()
        await mgr.push("u2", "moment", "m1", {"moment_id": 1})
        assert len(mgr.offline_queues["u2"]) == 1
    asyncio.run(_run())


def test_register_replays_offline():
    async def _run():
        mgr = ConnectionManager()
        # 离线期间产生事件 → 入队
        await mgr.push("u3", "message", "e1", {"content": "hello"})

        ws = FakeWebSocket()
        await mgr.register("u3", ws)  # 注册时补发
        assert len(ws.sent) == 1
        assert "e1" in ws.sent[0]
        assert mgr.offline_queues.get("u3") == []  # 补发后清空
    asyncio.run(_run())


def test_unregister():
    async def _run():
        mgr = ConnectionManager()
        ws = FakeWebSocket()
        await mgr.register("u4", ws)
        await mgr.unregister("u4", ws)
        assert mgr.get_online_count("u4") == 0
        assert "u4" not in mgr.get_all_online()
    asyncio.run(_run())
