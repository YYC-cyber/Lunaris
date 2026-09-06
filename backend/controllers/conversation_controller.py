# backend/controllers/conversation_controller.py
"""会话路由（FRI-06）—— 真人好友之间的一对一聊天。"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from middleware.auth_middleware import get_current_user
from models.user import User
from services.conversation_service import ConversationService

router = APIRouter()


class SendIn(BaseModel):
    user_id: str = Field(..., description="接收者 user_id")
    content: str = Field("", max_length=2000, description="内容（发纯表情或图片时可为空）")
    msg_type: str = Field("text", pattern="^(text|sticker|image|voice)$")
    sticker_id: int | None = None   # 表情包（STK）
    image_url: str | None = None    # 图片 URL
    voice_url: str | None = None    # 语音 URL


@router.post("")
async def send_message(
    data: SendIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """给某用户发送私聊消息（需互为好友；自动创建会话）。"""
    try:
        receiver_id = uuid.UUID(data.user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效 user_id")
    try:
        msg = await ConversationService.send_message(
            db,
            user.id,
            receiver_id,
            data.content,
            data.msg_type,
            data.sticker_id,
            data.image_url,
            data.voice_url,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # WS 推送（发送者多端同步 + 接收者实时）
    from services.notify_service import push_user_message
    payload = {
        "message_id": msg.id,
        "conversation_id": msg.conversation_id,
        "sender_id": str(user.id),
        "content": msg.content,
        "msg_type": msg.msg_type,
        "image_url": msg.image_url if msg.msg_type == "image" else None,
        "voice_url": msg.voice_url if msg.msg_type == "voice" else None,
        "created_at": msg.created_at.isoformat() if msg.created_at else "",
    }
    try:
        await push_user_message(str(user.id), payload)      # 自己（多端）
        await push_user_message(str(receiver_id), payload)  # 对方
    except Exception as e:
        print(f"⚠️ 用户消息推送失败: {e}")

    return {"success": True, "message": payload}


@router.get("")
async def list_conversations(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """我的会话列表（含对方信息 + 最后消息预览，按最新排序）。"""
    return {"data": await ConversationService.list_conversations(db, user.id)}


@router.get("/{conversation_id}/messages")
async def list_messages(
    conversation_id: int,
    user: User = Depends(get_current_user),
    offset: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """某会话的消息历史。"""
    try:
        msgs = await ConversationService.list_messages(db, user.id, conversation_id, offset, limit)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {"data": msgs, "offset": offset, "count": len(msgs)}
