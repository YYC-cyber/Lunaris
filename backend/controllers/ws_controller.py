# backend/controllers/ws_controller.py
"""WebSocket 控制器 —— /api/ws 端点。

【职责】
- JWT 鉴权（查询参数 ?token=...）
- 接受连接，注册到 ConnectionManager（自动补发离线事件）
- 心跳处理（客户端 ping → 服务端 pong）
- 异常断开时自动注销
"""
import json
import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from jose import JWTError, jwt

from config.settings import get_settings
from config.database import AsyncSessionLocal
from ws.connection_manager import get_connection_manager

router = APIRouter()
settings = get_settings()
manager = get_connection_manager()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT Token"),
):
    """
    WebSocket 连接端点。

    连接示例：
    ws://localhost:8000/api/ws?token=eyJhbGciOiJIUzI1NiIs...
    """
    # 1. JWT 鉴权（在 accept 之前，失败直接以 1008 拒绝）
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except JWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 2. 接受连接
    await websocket.accept()
    print(f"🔌 WebSocket 连接建立: user_id={user_id}")

    # 3. 注册连接（自动补发离线消息）
    await manager.register(user_id, websocket)

    # P2-05: 更新用户最后活跃时间，广播上线事件
    try:
        async with AsyncSessionLocal() as db:
            from services.v1_0.user_status_service import UserStatusService
            user_uuid = uuid.UUID(user_id)
            await UserStatusService.update_user_last_seen(db, user_uuid)
            await UserStatusService.broadcast_user_event(user_uuid, is_online=True)
    except Exception as e:
        print(f"⚠️ 更新用户状态失败: {e}")

    try:
        # 4. 心跳循环：接收客户端消息（ping / ack）
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
                msg_type = data.get("type")
                if msg_type == "ping":
                    # 回复 pong（回显客户端时间戳）
                    await websocket.send_text(
                        json.dumps({"type": "pong", "ts": data.get("ts")})
                    )
                    # P1-04: 更新最后 pong 时间戳（用于空闲检测）
                    await manager.handle_pong(user_id)
                elif msg_type == "ack":
                    # 客户端确认送达，忽略
                    pass
                else:
                    # 未知消息类型，忽略
                    pass
            except json.JSONDecodeError:
                # 非 JSON 消息，忽略
                pass
    except WebSocketDisconnect:
        # 5. 正常断开
        await manager.unregister(user_id, websocket)
        print(f"🔌 WebSocket 连接断开: user_id={user_id}")

        # P2-05: 广播下线事件
        try:
            user_uuid = uuid.UUID(user_id)
            from services.v1_0.user_status_service import UserStatusService
            await UserStatusService.broadcast_user_event(user_uuid, is_online=False)
        except Exception as e:
            print(f"⚠️ 广播下线事件失败: {e}")
    except Exception as e:
        print(f"⚠️ WebSocket 异常: {e}")
        await manager.unregister(user_id, websocket)
