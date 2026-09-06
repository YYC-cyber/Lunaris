# backend/services/notify_service.py
"""通知服务 —— 全系统唯一的推送出口。

【职责】
- 封装 ConnectionManager.push，提供语义化的推送方法（push_moment / push_message / push_notification）
- 统一生成事件 ID
- 供 chat_service / moment_service / tasks 调用
"""
import uuid
from typing import Any, Dict, Optional

from ws.connection_manager import get_connection_manager

_manager = get_connection_manager()


def _generate_event_id() -> str:
    return f"evt_{uuid.uuid4().hex[:16]}"


async def push_moment(user_id: str, moment_data: Dict[str, Any]) -> None:
    """推送朋友圈新动态。

    :param user_id: 目标用户 ID（字符串）
    :param moment_data: 动态数据（id, soul_id, content, images, topic_tags, created_at）
    """
    await _manager.push(
        user_id=user_id,
        event_type="moment",
        event_id=_generate_event_id(),
        data=moment_data,
    )


async def push_message(user_id: str, message_data: Dict[str, Any]) -> None:
    """推送新消息（聊天私信 / AI 回复）。

    :param user_id: 目标用户 ID（字符串）
    :param message_data: 消息数据（user_message_id, ai_message_id, content, emotion, created_at）
    """
    await _manager.push(
        user_id=user_id,
        event_type="message",
        event_id=_generate_event_id(),
        data=message_data,
    )


async def push_user_message(user_id: str, message_data: Dict[str, Any]) -> None:
    """推送真人用户间的私聊消息（FRI-06，经 WS 实时送达）。"""
    await _manager.push(
        user_id=user_id,
        event_type="user_message",
        event_id=_generate_event_id(),
        data=message_data,
    )


async def push_notification(
    user_id: str,
    title: str,
    body: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """推送系统通知。

    :param user_id: 目标用户 ID（字符串）
    :param title: 通知标题
    :param body: 通知内容
    :param metadata: 附加数据
    """
    data: Dict[str, Any] = {"title": title, "body": body}
    if metadata:
        data["metadata"] = metadata
    await _manager.push(
        user_id=user_id,
        event_type="notification",
        event_id=_generate_event_id(),
        data=data,
    )
