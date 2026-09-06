# backend/controllers/chat_controller.py
import uuid
import asyncio
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel, Field

from config.database import get_db, AsyncSessionLocal
from core import memory as memory_engine
from middleware.auth_middleware import get_current_user
from models.user import User
from services.chat_service import (
    ChatService,
    _FALLBACK_REPLY,
    _LLM_ERROR_PREFIX,
    _is_meaningful,
    clean_generated_text,
)
from models.soul import Soul
from models.friendship import Friendship
from dao.friendship_dao import FriendshipDAO
from dao.message_dao import MessageDAO
from dao.soul_dao import SoulDAO
from clients.llm_client import LLMClient
from ws.connection_manager import get_connection_manager

router = APIRouter()

# 持有后台流式任务引用，防止被垃圾回收
_stream_tasks: set = set()


# ---- 请求体 DTO ----
class ChatRequest(BaseModel):
    soul_id: int = Field(..., description="角色 ID")
    message: str = Field("", max_length=2000, description="用户消息（发纯表情或语音时可为空）")
    sticker_id: int | None = Field(None, description="用户发的表情包 ID")
    voice_url: str | None = Field(None, description="用户发的语音文件 URL")
    stream: bool = Field(False, description="是否启用流式输出")


# ---- 响应体 DTO ----
class ChatResponse(BaseModel):
    user_message_id: int
    ai_message_id: int
    content: str | None
    emotion: str
    created_at: str
    sticker_id: int | None = None
    sticker_name: str | None = None
    sticker_url: str | None = None   # AI 回的表情包（STK）
    sticker_emotion: str | None = None
    sticker_emoji: str | None = None
    voice_url: str | None = None
    original_text: str | None = None


class StreamResponse(BaseModel):
    request_id: str
    status: str = "streaming"


# ---- 后台任务：流式处理 ----
async def _process_streaming_chat(
    user_id: str,
    soul_id: int,
    request_id: str,
    system_prompt: str,
    history: list,
    user_message: str,
    user_msg_id: int,
    llm_config: dict,
    intimacy: int = 0,
):
    """
    后台任务：调用 LLM 流式接口，通过 WebSocket 推送块，结束后保存 AI 回复
    """
    manager = get_connection_manager()
    try:
        # 未配置/未授权 → 直接推送提示，不调用 LLM
        if not llm_config.get("api_key"):
            hint = "（未配置 AI 服务：请在设置中配置 LLM API，或联系管理员开通权限）"
            await manager.push(
                user_id=user_id, event_type="stream_chunk",
                event_id=f"{request_id}_hint",
                data={"request_id": request_id, "delta": hint},
            )
            await manager.push(
                user_id=user_id, event_type="stream_end",
                event_id=f"{request_id}_end",
                data={"request_id": request_id, "full_content": hint},
            )
            return

        # BYOK：用用户自己的 LLM 配置
        llm = LLMClient(
            api_key=llm_config.get("api_key") or None,
            base_url=llm_config.get("base_url"),
            model=llm_config.get("model"),
        )
        full_content = ""

        # 1. 流式生成
        generator = llm.chat_completion_stream(
            system_prompt=system_prompt,
            history=history,
            user_message=user_message,
        )

        async for chunk in generator:
            if chunk:
                full_content += chunk
                # 推送 stream_chunk 事件
                await manager.push(
                    user_id=user_id,
                    event_type="stream_chunk",
                    event_id=f"{request_id}_{uuid.uuid4().hex[:8]}",
                    data={"request_id": request_id, "delta": chunk},
                )

        # 1.5 AI 延迟回复（人性化）：流式传输后加入延迟，让对话更自然
        import random
        delay = random.uniform(0.5, 1.5)  # 流式的延迟稍短一些（因为已经逐字显示了）
        await asyncio.sleep(delay)

        # 清理 LLM 回复中的 SSML 标记和其他不应出现的文本
        full_content = clean_generated_text(full_content)

        # 2. 保存 AI 回复到数据库（独立会话）
        async with AsyncSessionLocal() as db:
            # 先检查用户消息是否存在（防止重复保存）
            from models.message import Message
            stmt = select(Message).where(Message.id == user_msg_id)
            result = await db.execute(stmt)
            existing_user_msg = result.scalar_one_or_none()
            if not existing_user_msg:
                print(f"⚠️ 用户消息 {user_msg_id} 不存在，无法保存 AI 回复")
                return

            # 判断是否有有效内容
            if not full_content:
                full_content = "（我暂时无法回答，请稍后再试）"

            # 保存 AI 回复（含亲密度成长；save_ai_response 会提取情绪）
            ai_msg = await ChatService.save_ai_response(
                db=db,
                user_id=uuid.UUID(user_id),
                soul_id=soul_id,
                content=full_content,
                emotion="neutral",
            )

            # 后台合成 AI 语音（角色性格音色 + 提取的情绪语速；错误回复不合成）
            voice_url = None
            if not full_content.startswith(_LLM_ERROR_PREFIX) and full_content != _FALLBACK_REPLY:
                voice_url = await ChatService._synthesize_tts_for_message(
                    db, ai_msg, soul_id, full_content, ai_msg.emotion, intimacy
                )

            # 语音生成完成后再结束流式消息，确保前端同时拿到 voice_url 和原文。
            await manager.push(
                user_id=user_id,
                event_type="stream_end",
                event_id=f"{request_id}_end",
                data={
                    "request_id": request_id,
                    "full_content": None if voice_url else full_content,
                    "original_text": full_content if voice_url else None,
                    "voice_url": voice_url,
                    "emotion": ai_msg.emotion,
                },
            )

            await manager.push(
                user_id=user_id,
                event_type="typing_end",
                event_id=f"{request_id}_typing_end",
                data={"soul_id": soul_id, "request_id": request_id},
            )

            # 推送消息事件（多端同步 RT-05）
            # 重要：有 voice_url 则只推送语音不推送文字（用户右键菜单可转文字）
            try:
                from services.notify_service import push_message
                await push_message(
                    user_id=user_id,
                    message_data={
                        "user_message_id": user_msg_id,
                        "ai_message_id": ai_msg.id,
                        "content": None if voice_url else full_content,
                        "original_text": full_content if voice_url else None,
                        "emotion": "neutral",
                        "created_at": ai_msg.created_at.isoformat() if ai_msg.created_at else "",
                        "voice_url": voice_url,
                    },
                )
            except Exception as pe:
                print(f"⚠️ 流式消息推送失败: {pe}")

            # 记忆提取（与非流式一致）
            if full_content != _FALLBACK_REPLY and _is_meaningful(user_message):
                memory_engine.schedule_extraction(
                    uuid.UUID(user_id), soul_id, user_message, full_content
                )

            print(f"✅ 流式消息已保存: {full_content[:30]}...")

    except Exception as e:
        print(f"⚠️ 流式聊天失败: {e}")
        # 推送错误通知（带用户可读的原因提示）
        from clients.llm_client import friendly_llm_error
        hint = friendly_llm_error(e, model=(llm_config.get("model") or ""))
        await manager.push(
            user_id=user_id,
            event_type="notification",
            event_id=f"{request_id}_error",
            data={"title": "AI 服务出错了", "body": hint},
        )


# ---- 主接口 ----
# 注意：main.py 挂载前缀是 /v1/chat，这里路由只需 /completions，拼成 /v1/chat/completions
@router.post("/completions")
async def chat_completion(
    req: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    发送消息并获取 AI 回复

    支持两种模式：
    - stream=false（默认）：等待完整回复，返回 JSON
    - stream=true：立即返回 request_id，回复通过 WebSocket 流式推送

    流式模式需要 WebSocket 连接：
    ws://localhost:8000/api/ws?token=<JWT>
    """
    # 1. 当前用户来自 JWT token（get_current_user 已校验身份）
    uid = user.id

    # 2. 验证角色
    stmt = select(Soul).where(Soul.id == req.soul_id)
    result = await db.execute(stmt)
    soul = result.scalar_one_or_none()
    if not soul:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在",
        )

    # 4. 验证配对关系
    stmt = select(Friendship).where(
        Friendship.user_id == uid,
        Friendship.soul_id == req.soul_id,
    )
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="你还没有配对过该角色",
        )

    # 5. 判断是否流式
    if req.stream:
        # ---- 流式模式 ----
        # 5a. 准备上下文（保存用户消息，获取人设/历史/记忆）
        user_msg, system_prompt, history, friendship = await ChatService.prepare_stream(
            db=db,
            user_id=uid,
            soul_id=req.soul_id,
            content=req.message,
        )

        # 5b. 生成请求 ID
        request_id = uuid.uuid4().hex[:16]

        # 5c. 解析用户 LLM 配置（BYOK）
        from services.api_config_service import ApiConfigService
        llm_config = await ApiConfigService.resolve(db, user.id, "llm")

        # 5c.5. 发送 typing_start 事件（前端显示 Typing 气泡）
        manager = get_connection_manager()
        await manager.push(
            user_id=str(uid),
            event_type="typing_start",
            event_id=f"{request_id}_typing_start",
            data={"soul_id": req.soul_id, "request_id": request_id},
        )

        # 5d. 启动后台任务（持有引用防 GC）
        task = asyncio.create_task(
            _process_streaming_chat(
                user_id=str(uid),
                soul_id=req.soul_id,
                request_id=request_id,
                system_prompt=system_prompt,
                history=history,
                user_message=req.message,
                user_msg_id=user_msg.id,
                llm_config=llm_config,
                intimacy=friendship.intimacy_level if friendship else 0,
            )
        )
        _stream_tasks.add(task)
        task.add_done_callback(_stream_tasks.discard)

        # 5d. 立即返回
        return StreamResponse(request_id=request_id)

    # ---- 非流式模式 ----
    if not req.message.strip() and not req.sticker_id and not req.voice_url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="消息、表情包或语音不能都为空")
    try:
        result = await ChatService.send_message(
            db=db,
            user_id=uid,
            soul_id=req.soul_id,
            content=req.message,
            sticker_id=req.sticker_id,
            voice_url=req.voice_url,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"聊天服务错误: {str(e)}",
        )

    return ChatResponse(
        user_message_id=result["user_message_id"],
        ai_message_id=result["ai_message_id"],
        content=result["content"],
        emotion=result["emotion"],
        created_at=result["created_at"],
        sticker_id=(result.get("reply_sticker") or {}).get("id"),
        sticker_name=(result.get("reply_sticker") or {}).get("name"),
        sticker_url=(result.get("reply_sticker") or {}).get("image_url"),
        sticker_emotion=(result.get("reply_sticker") or {}).get("emotion"),
        sticker_emoji=(result.get("reply_sticker") or {}).get("sticker_emoji"),
        voice_url=result.get("voice_url"),
        original_text=result.get("original_text"),
    )


# ---- 聊天历史（CHAT-06 / CHAT-07）----
@router.get("/history")
async def get_chat_history(
    soul_id: int,
    user: User = Depends(get_current_user),
    offset: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """分页获取当前用户某会话的聊天历史。"""
    items = await ChatService.get_history(db, user.id, soul_id, offset, limit)
    return {"data": items, "offset": offset, "count": len(items)}


@router.delete("/history")
async def clear_chat_history(
    soul_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """清空当前用户与某个 AI 伴侣会话的全部聊天记录（保留伴侣关系）。"""
    deleted = await ChatService.clear_history(db, user.id, soul_id)
    return {"success": True, "deleted": deleted}


@router.get("/friendships")
async def get_friendships(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户所有配对关系、亲密度、最近消息、当日心语。"""
    from models.message import Message

    stmt = select(Friendship).where(Friendship.user_id == user.id)
    friendships = list((await db.execute(stmt)).scalars().all())

    result = []
    for f in friendships:
        # 获取该配对的最后一条 AI 消息（用作预览）
        msg_stmt = (
            select(Message)
            .where(Message.user_id == user.id, Message.soul_id == f.soul_id, Message.sender_type == "ai")
            .order_by(desc(Message.id))
            .limit(1)
        )
        last_msg = (await db.execute(msg_stmt)).scalar_one_or_none()

        # 获取角色信息（包括 daily_motto）
        soul = await SoulDAO.get(db, f.soul_id)

        result.append({
            "soul_id": f.soul_id,
            "intimacy_level": f.intimacy_level or 0,
            "last_chat_at": f.last_chat_at.isoformat() if f.last_chat_at else None,
            "last_message_preview": (last_msg.content[:30] + "...") if last_msg and len(last_msg.content) > 30 else (last_msg.content if last_msg else ""),
            "daily_motto": soul.daily_motto if soul else "今天也要开心呀！",  # 默认心语
        })

    return result


@router.delete("/message/{message_id}")
async def recall_message(
    message_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """撤回某条消息（仅自己发的消息可撤回）。"""
    msg = await MessageDAO.get(db, message_id)
    if not msg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="消息不存在",
        )
    if msg.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能撤回自己的消息",
        )
    if msg.sender_type != "user":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="AI 消息不能撤回",
        )

    success = await MessageDAO.recall(db, message_id)
    return {"success": success}


# ==================== P1-01: 消息编辑 ====================
class EditMessageRequest(BaseModel):
    new_content: str = Field(..., max_length=2000, description="新的消息内容")


@router.patch("/message/{message_id}")
async def edit_message(
    message_id: int,
    req: EditMessageRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """编辑消息（需在发送后 15 分钟内编辑）。"""
    success, message = await ChatService.edit_message(
        db=db,
        message_id=message_id,
        new_content=req.new_content,
        user_id=user.id,
        time_window_minutes=15,
    )

    if not success:
        if "不存在" in message:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
        elif "只能编辑" in message or "不能编辑" in message:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    # 返回更新后的消息
    msg = await MessageDAO.get(db, message_id)
    return {
        "id": msg.id,
        "content": msg.content,
        "is_edited": msg.is_edited,
        "edited_at": msg.edited_at.isoformat() if msg.edited_at else None,
    }


# ==================== P1-02: 消息转发 ====================
class ForwardMessageRequest(BaseModel):
    target_user_id: Optional[uuid.UUID] = Field(None, description="目标站内好友用户 ID")


@router.post("/message/{message_id}/forward")
async def forward_message(
    message_id: int,
    req: ForwardMessageRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """转发消息到指定的站内好友。"""
    success, message, new_message_id = await ChatService.forward_message(
        db=db,
        message_id=message_id,
        target_user_id=req.target_user_id,
        user_id=user.id,
    )

    if not success:
        if "过于频繁" in message:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=message)
        elif "不存在" in message or "已撤回" in message or "必须指定" in message or "好友" in message:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message)

    forwarded = await MessageDAO.get(db, new_message_id) if new_message_id else None
    if forwarded and req.target_user_id:
        payload = {
            "message_id": forwarded.id,
            "conversation_id": forwarded.conversation_id,
            "sender_id": str(user.id),
            "content": forwarded.content,
            "msg_type": forwarded.msg_type,
            "image_url": forwarded.image_url if forwarded.msg_type == "image" else None,
            "voice_url": forwarded.voice_url if forwarded.msg_type == "voice" else None,
            "created_at": forwarded.created_at.isoformat() if forwarded.created_at else "",
            "forwarded_from_id": forwarded.forwarded_from_id,
        }
        try:
            from services.notify_service import push_user_message
            await push_user_message(str(user.id), payload)
            await push_user_message(str(req.target_user_id), payload)
        except Exception as e:
            logger.warning("转发消息推送失败: %s", e)

    return {
        "message_id": new_message_id,
        "conversation_id": forwarded.conversation_id if forwarded else None,
    }


# ==================== P1-03: 消息收藏 ====================
class AddFavoriteRequest(BaseModel):
    category: str = Field("默认", description="收藏分类")


@router.post("/message/{message_id}/favorite")
async def add_favorite(
    message_id: int,
    req: AddFavoriteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """添加消息到收藏夹。"""
    from services.message_favorite_service import MessageFavoriteService

    result = await MessageFavoriteService.add(
        db=db,
        user_id=user.id,
        message_id=message_id,
        category=req.category,
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="消息不存在或已收藏",
        )

    return result


@router.delete("/message/{message_id}/favorite")
async def remove_favorite(
    message_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """从收藏夹移除消息。"""
    from services.message_favorite_service import MessageFavoriteService

    success = await MessageFavoriteService.remove(
        db=db,
        user_id=user.id,
        message_id=message_id,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="消息未被收藏",
        )

    return {"success": True}


@router.get("/message/favorites")
async def list_favorites(
    category: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取用户收藏的消息列表。"""
    from services.message_favorite_service import MessageFavoriteService

    if keyword:
        result = await MessageFavoriteService.search(
            db=db,
            user_id=user.id,
            keyword=keyword,
            limit=limit,
            offset=offset,
        )
    else:
        result = await MessageFavoriteService.list(
            db=db,
            user_id=user.id,
            category=category,
            limit=limit,
            offset=offset,
        )

    return result
