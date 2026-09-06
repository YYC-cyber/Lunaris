# backend/ws/streamer.py
"""流式转发器 —— 将聊天流式响应通过 WebSocket 推送。

【职责】
- 包装异步生成器，逐步推送 stream_chunk 事件
- 结束时推送 stream_end
- 异常时推送 notification 提示
"""
import uuid
from typing import Any, AsyncGenerator, Dict

from .connection_manager import get_connection_manager


class Streamer:
    @staticmethod
    async def stream_to_ws(
        user_id: str,
        request_id: str,
        generator: AsyncGenerator[str, None],
    ) -> None:
        """
        将流式生成器逐块推送给用户

        :param user_id: 目标用户 ID
        :param request_id: 请求 ID（用于关联前后端）
        :param generator: 异步生成器，yield 字符串块
        """
        manager = get_connection_manager()
        full_content = ""

        try:
            async for chunk in generator:
                if not chunk:
                    continue
                full_content += chunk
                event_id = f"{request_id}_{uuid.uuid4().hex[:8]}"
                await manager.push(
                    user_id=user_id,
                    event_type="stream_chunk",
                    event_id=event_id,
                    data={"request_id": request_id, "delta": chunk},
                )

            # 推送结束事件
            await manager.push(
                user_id=user_id,
                event_type="stream_end",
                event_id=f"{request_id}_end",
                data={"request_id": request_id, "full_content": full_content},
            )
        except Exception as e:
            await manager.push(
                user_id=user_id,
                event_type="notification",
                event_id=f"{request_id}_error",
                data={"title": "流式发送失败", "body": str(e)},
            )
