"""群聊控制器"""
import uuid
import asyncio
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db, AsyncSessionLocal
from middleware.auth_middleware import get_current_user
from models.user import User
from services.group_chat_service import GroupChatService
from ws.connection_manager import get_connection_manager

router = APIRouter()


def _extract_mention_names(content: str) -> set[str]:
    """Extract @mentions from message content with Unicode name support."""
    import re
    normalized = (content or "").replace("\u3000", " ")
    return {
        match.group(1).strip().lower()
        for match in re.finditer(r"@\s*([^\s@,，。！？!?]+)", normalized)
        if match.group(1).strip()
    }


# ================== 请求/响应 DTO ==================

class CreateGroupRequest(BaseModel):
    """创建群聊请求"""
    group_name: str
    group_type: str  # ai_only / human_only / mixed
    ai_soul_ids: Optional[List[int]] = None  # AI 成员 ID
    human_user_ids: Optional[List[str]] = None  # 邀请的真人用户 ID
    auto_delete_hours: Optional[int] = None  # 消息自动删除时长（小时）


class SendGroupMessageRequest(BaseModel):
    """发送群消息请求"""
    content: str
    voice_url: Optional[str] = None
    mentioned_user_ids: Optional[List[str]] = None


class InviteMemberRequest(BaseModel):
    """邀请成员请求"""
    invitee_id: str


class RespondInvitationRequest(BaseModel):
    """响应邀请请求"""
    invitation_id: int
    accept: bool


class AddMemberRequest(BaseModel):
    member_type: str
    user_id: Optional[str] = None
    soul_id: Optional[int] = None


class UpdateMemberRequest(BaseModel):
    role: str


class UpdateGroupSettingsRequest(BaseModel):
    group_name: Optional[str] = None
    announcement: Optional[str] = None


class TransferOwnerRequest(BaseModel):
    """转让群主权限请求"""
    new_owner_member_id: int  # 新群主的 group_members 表记录 ID


class AddGroupMemoryRequest(BaseModel):
    """添加群记忆请求"""
    memory_type: str  # 'event', 'member_info', 'group_rule', 'topic'
    content: str


# ================== API 端点 ==================

@router.post("/groups")
async def create_group(
    req: CreateGroupRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建群聊"""
    try:
        # 转换 user_id 列表
        human_ids = None
        if req.human_user_ids:
            human_ids = [uuid.UUID(uid) for uid in req.human_user_ids]

        group_info = await GroupChatService.create_group(
            db,
            user_id=user.id,
            group_name=req.group_name,
            group_type=req.group_type,
            ai_soul_ids=req.ai_soul_ids,
            human_user_ids=human_ids,
            auto_delete_hours=req.auto_delete_hours,
        )
        return group_info
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/groups/{group_id}")
async def get_group(
    group_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取群聊详情"""
    group_info = await GroupChatService.get_group_info(db, group_id)
    if not group_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="群聊不存在",
        )

    # 检查权限：用户必须是群成员
    from dao.group_chat_dao import GroupMemberDAO
    is_member = await GroupMemberDAO.is_member(db, group_id, user.id)
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="你不是这个群的成员",
        )

    return group_info


@router.get("/groups")
async def list_groups(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取用户的所有群聊"""
    from dao.group_chat_dao import GroupChatDAO
    groups = await GroupChatDAO.list_by_user(db, user.id)
    result = []
    for g in groups:
        group_info = await GroupChatService.get_group_info(db, g.id)
        if group_info:
            result.append(group_info)
    return result


@router.post("/groups/{group_id}/messages")
async def send_group_message(
    group_id: int,
    req: SendGroupMessageRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """发送群消息"""
    try:
        # 检查权限
        from dao.group_chat_dao import GroupMemberDAO, GroupChatDAO
        is_member = await GroupMemberDAO.is_member(db, group_id, user.id)
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="你不是这个群的成员",
            )

        # 发送消息
        message = await GroupChatService.send_message(
            db,
            group_id=group_id,
            sender_type="user",
            content=req.content,
            sender_id=user.id,
            voice_url=req.voice_url,
        )

        # 通过 WebSocket 推送给所有群成员
        manager = get_connection_manager()
        all_members = await GroupMemberDAO.get_members(db, group_id, status="active")

        print(f"📤 群 {group_id} 用户消息 {message['id']}: 推送给 {len([m for m in all_members if m.member_type == 'human'])} 个真人成员")
        for member in all_members:
            if member.member_type == "human":
                print(f"  → 推送给用户 {member.member_id}")
                await manager.push(
                    user_id=str(member.member_id),
                    event_type="group_message",
                    event_id=f"group_{group_id}_{message['id']}",
                    data={
                        "group_id": group_id,
                        "message": message,
                    },
                )

        # 可靠触发 AI 回应。消息已经先通过 WebSocket 推送，随后等待 AI
        # 处理完成，避免请求结束后后台 task 被回收或异常无人感知。
        await _trigger_ai_responses(
            group_id,
            req.content,
            user.id,
            req.mentioned_user_ids or [],
        )

        return message
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/groups/{group_id}/messages")
async def get_group_messages(
    group_id: int,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取群消息历史"""
    # 检查权限
    from dao.group_chat_dao import GroupMemberDAO
    is_member = await GroupMemberDAO.is_member(db, group_id, user.id)
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="你不是这个群的成员",
        )

    messages = await GroupChatService.get_message_history(db, group_id, limit=limit)
    # 合并连续消息
    merged = GroupChatService.merge_consecutive_messages(messages)
    return {"messages": merged}


@router.post("/groups/{group_id}/invite")
async def invite_member(
    group_id: int,
    req: InviteMemberRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """邀请成员加入群聊"""
    try:
        invitee_id = uuid.UUID(req.invitee_id)
        invitation = await GroupChatService.invite_member(
            db,
            group_id=group_id,
            inviter_id=user.id,
            invitee_id=invitee_id,
        )

        # 推送通知给被邀请者
        manager = get_connection_manager()
        await manager.push(
            user_id=str(invitee_id),
            event_type="group_invitation",
            event_id=f"invitation_{invitation['id']}",
            data=invitation,
        )

        return invitation
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/groups/{group_id}/members")
async def add_group_member(
    group_id: int,
    req: AddMemberRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        member_id = uuid.UUID(req.user_id) if req.user_id else None
        result = await GroupChatService.add_member(
            db, group_id, user.id, req.member_type, member_id, req.soul_id
        )
        await db.commit()
        return result
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/groups/{group_id}/members/{member_id}")
async def update_group_member(
    group_id: int,
    member_id: int,
    req: UpdateMemberRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await GroupChatService.update_member(
            db, group_id, member_id, user.id, req.role
        )
        await db.commit()
        return result
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/groups/{group_id}/members/{member_id}")
async def delete_group_member(
    group_id: int,
    member_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await GroupChatService.remove_member(db, group_id, member_id, user.id)
        await db.commit()
        return {"ok": True}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/groups/{group_id}/settings")
async def update_group_settings(
    group_id: int,
    req: UpdateGroupSettingsRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await GroupChatService.update_group_settings(
            db, group_id, user.id, req.group_name, req.announcement
        )
        await db.commit()
        return result
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/invitations/{invitation_id}/respond")
async def respond_to_invitation(
    invitation_id: int,
    req: RespondInvitationRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """响应邀请"""
    try:
        result = await GroupChatService.respond_to_invitation(
            db,
            invitation_id=invitation_id,
            accept=req.accept,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/invitations/pending")
async def get_pending_invitations(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取待处理的邀请"""
    from dao.group_chat_dao import GroupInvitationDAO, GroupChatDAO
    from dao.user_dao import UserDAO

    invitations = await GroupInvitationDAO.get_pending_invitations(db, user.id)

    result = []
    for inv in invitations:
        group = await GroupChatDAO.get(db, inv.group_id)
        inviter = await UserDAO.get(db, inv.inviter_id)
        result.append({
            "id": inv.id,
            "group_id": inv.group_id,
            "group_name": group.group_name if group else "Unknown",
            "inviter_id": str(inv.inviter_id),
            "inviter_name": inviter.nickname if inviter else "Unknown",
            "created_at": inv.created_at.isoformat(),
            "expires_at": inv.expires_at.isoformat(),
        })

    return {"invitations": result}


@router.delete("/groups/{group_id}/leave")
async def leave_group(
    group_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """成员主动退出群聊"""
    try:
        await GroupChatService.leave_group(db, group_id, user.id)
        await db.commit()
        return {"ok": True, "message": "已退出群聊"}
    except (ValueError, PermissionError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/groups/{group_id}/transfer-owner")
async def transfer_owner(
    group_id: int,
    req: TransferOwnerRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """转让群主权限"""
    try:
        result = await GroupChatService.transfer_owner(
            db, group_id, user.id, req.new_owner_member_id
        )
        await db.commit()
        return result
    except (ValueError, PermissionError) as e:
        error_code = (
            status.HTTP_403_FORBIDDEN if isinstance(e, PermissionError)
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(
            status_code=error_code,
            detail=str(e),
        )


# ================== 后台任务：AI 回应触发 ==================

async def _trigger_ai_responses(
    group_id: int,
    message_content: str,
    user_id: uuid.UUID,
    mentioned_user_ids: Optional[List[str]] = None,
):
    """后台任务：遍历群内 AI 成员，判断是否应该回应，触发 LLM 生成"""
    import logging
    logger = logging.getLogger(__name__)

    try:
        logger.info(f"🔵 [群聊 AI] 开始检查群 {group_id} 是否需要 AI 回应")
        from dao.group_chat_dao import GroupMemberDAO, GroupChatDAO
        from services.group_response_strategy import GroupResponseStrategy
        from services.chat_service import ChatService
        from services import context_service
        from dao.friendship_dao import FriendshipDAO
        from dao.soul_dao import SoulDAO
        from common.helpers import extract_emotion

        # 用独立 session（不依赖请求的 db 会话）
        async with AsyncSessionLocal() as session:
            # 获取群聊信息
            group = await GroupChatDAO.get(session, group_id)
            if not group:
                logger.warning(f"❌ 群 {group_id} 不存在")
                return

            logger.info(f"📍 群 {group_id} 类型: {group.group_type}")

            # 获取群内所有成员
            members = await GroupMemberDAO.get_members(session, group_id, status="active")
            ai_members = [m for m in members if m.member_type == "ai"]

            logger.info(f"🤖 群内 AI 成员数: {len(ai_members)}")

            if not ai_members:
                logger.info(f"⏭️ 群 {group_id} 没有 AI 成员，跳过")
                return

            mentioned_ids = {str(value).strip().lower() for value in (mentioned_user_ids or []) if value}
            mentioned_names = _extract_mention_names(message_content)
            mentioned_ai_soul_ids: set[int] = set()

            for ai_member in ai_members:
                soul = await SoulDAO.get(session, ai_member.soul_id)
                ai_identifiers = {
                    str(ai_member.id).lower(),
                    str(ai_member.soul_id).lower(),
                }
                if soul:
                    ai_identifiers.update({
                        str(soul.display_name or "").strip().lower(),
                        str(soul.name or "").strip().lower(),
                    })

                if mentioned_ids.intersection(ai_identifiers) or mentioned_names.intersection(ai_identifiers):
                    mentioned_ai_soul_ids.add(ai_member.soul_id)

            logger.info(
                "🎯 群 %s @解析: ids=%s names=%s ai_soul_ids=%s",
                group_id,
                sorted(mentioned_ids),
                sorted(mentioned_names),
                sorted(mentioned_ai_soul_ids),
            )

            # 逐个 AI 成员判断是否回应
            trigger_all_ai = not mentioned_ai_soul_ids
            for ai_member in ai_members:
                try:
                    logger.info(f"🔍 检查 AI {ai_member.soul_id} 是否应该回应")
                    force_respond = ai_member.soul_id in mentioned_ai_soul_ids
                    if not trigger_all_ai and not force_respond:
                        logger.info(f"⏭️ AI {ai_member.soul_id} 未被 @，跳过")
                        continue

                    # 获取亲密度（使用当前发消息用户）
                    friendship = await FriendshipDAO.get_by_user_soul(session, user_id, ai_member.soul_id)
                    intimacy = friendship.intimacy_level if friendship else 0

                    # 判断是否应该回应（调用 9 规则评分系统）
                    should_respond = await GroupResponseStrategy.should_respond(
                        db=session,
                        ai_soul_id=ai_member.soul_id,
                        group_id=group_id,
                        last_message_content=message_content,
                        last_message_sender="user",
                        user_id=user_id,
                        group_type=group.group_type,
                        intimacy=intimacy,
                        mentioned_user_ids=mentioned_user_ids or [],
                        force_respond=force_respond,
                    )

                    if trigger_all_ai and group.group_type == "mixed":
                        should_respond = True

                    logger.info(f"📊 AI {ai_member.soul_id} 回应决定: {should_respond} force={force_respond}")

                    if not should_respond:
                        logger.info(f"⏭️ AI {ai_member.soul_id} 决定沉默")
                        continue

                    # 获取所有成员信息（用于 system prompt）
                    all_members = [
                        {"id": m.soul_id or m.member_id, "type": m.member_type, "name": "Unknown"}
                        for m in members
                    ]
                    # 补充真实名字
                    for m, db_member in zip(all_members, members):
                        if db_member.member_type == "ai":
                            from dao.soul_dao import SoulDAO
                            soul = await SoulDAO.get(session, db_member.soul_id)
                            m["name"] = soul.display_name if soul else "Unknown"
                        else:
                            from dao.user_dao import UserDAO
                            user = await UserDAO.get(session, db_member.member_id)
                            m["name"] = user.nickname if user else "Unknown"

                    # 构建 system prompt（包含群记忆）
                    system_prompt = await context_service.build_group_system_prompt(
                        session, user_id, ai_member.soul_id, group_id, intimacy, all_members, message_content,
                        is_mixed_group=(group.group_type == "mixed")
                    )

                    # 获取群聊历史
                    history = await ChatService.get_group_conversation_history(session, group_id, limit=10)

                    # 构建 LLM 客户端
                    llm = await ChatService._make_llm(session, user_id)
                    if llm is None:
                        logger.warning(f"⚠️ 用户 {user_id} / AI {ai_member.soul_id} 未配置 LLM")
                        await _publish_group_ai_message(
                            session,
                            group_id,
                            ai_member.soul_id,
                            "（未配置 AI 服务：请在设置中配置 LLM API，或联系管理员开通权限）",
                        )
                        continue

                    # 调用 LLM 生成回复
                    try:
                        logger.info(f"🚀 调用 LLM 生成 AI {ai_member.soul_id} 的回复")
                        from core.agent import get_agent
                        ai_response = await get_agent(user_id, ai_member.soul_id).run(
                            llm,
                            system_prompt=system_prompt,
                            history=history,
                            user_message=message_content,
                        )
                        logger.info(f"✅ AI {ai_member.soul_id} 生成回复: {ai_response[:50]}")
                    except Exception as e:
                        logger.exception(f"⚠️ AI {ai_member.soul_id} LLM 生成失败: {e}")
                        from clients.llm_client import friendly_llm_error
                        await _publish_group_ai_message(
                            session,
                            group_id,
                            ai_member.soul_id,
                            f"（AI 服务出错了：{friendly_llm_error(e, model=getattr(llm, 'model', ''))}）",
                        )
                        continue

                    # 提取情绪
                    emotion = extract_emotion(ai_response)

                    # 保存 AI 消息到数据库
                    ai_msg = await GroupChatService.send_message(
                        session,
                        group_id=group_id,
                        sender_type="ai",
                        content=ai_response,
                        soul_id=ai_member.soul_id,
                    )

                    logger.info(f"💾 AI {ai_member.soul_id} 消息已保存，ID: {ai_msg['id']}")

                    # 标记 AI 已发言（用于规则 6：不连续说话）
                    GroupResponseStrategy.mark_ai_spoke(ai_member.soul_id, group_id)

                    await _publish_group_message_to_humans(session, group_id, ai_msg)

                except Exception as e:
                    logger.exception(f"⚠️ AI 成员 {ai_member.soul_id} 处理失败: {e}")
                    continue

    except Exception as e:
        logger.exception(f"⚠️ AI 回应触发失败: {e}")


async def _publish_group_message_to_humans(
    session: AsyncSession,
    group_id: int,
    message: dict,
) -> None:
    """Push one normalized group message to every human member."""
    from dao.group_chat_dao import GroupMemberDAO

    manager = get_connection_manager()
    members = await GroupMemberDAO.get_members(session, group_id, status="active")
    human_members = [member for member in members if member.member_type == "human"]
    for member in human_members:
        await manager.push(
            user_id=str(member.member_id),
            event_type="group_message",
            event_id=f"group_{group_id}_{message['id']}_ai",
            data={"group_id": group_id, "message": message},
        )


async def _publish_group_ai_message(
    session: AsyncSession,
    group_id: int,
    soul_id: int,
    content: str,
) -> None:
    """Persist and publish a visible AI status/error message for the group."""
    message = await GroupChatService.send_message(
        session,
        group_id=group_id,
        sender_type="ai",
        content=content,
        soul_id=soul_id,
    )
    await _publish_group_message_to_humans(session, group_id, message)


# ================== 群记忆管理 ==================

@router.post("/groups/{group_id}/souls/{soul_id}/memories")
async def add_group_memory(
    group_id: int,
    soul_id: int,
    req: AddGroupMemoryRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """添加群记忆（仅群创建者可用）"""
    try:
        from dao.group_chat_dao import GroupChatDAO, GroupMemoryDAO

        # 检查权限（只有群创建者能添加记忆）
        group = await GroupChatDAO.get(db, group_id)
        if not group or group.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有群创建者能管理群记忆",
            )

        # 添加记忆
        memory = await GroupMemoryDAO.create(
            db,
            group_id=group_id,
            soul_id=soul_id,
            memory_type=req.memory_type,
            content=req.content,
        )
        await db.commit()

        return {
            "id": memory.id,
            "group_id": group_id,
            "soul_id": soul_id,
            "memory_type": req.memory_type,
            "content": req.content,
            "created_at": memory.created_at.isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/groups/{group_id}/souls/{soul_id}/memories/{memory_id}")
async def delete_group_memory(
    group_id: int,
    soul_id: int,
    memory_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除群记忆（仅群创建者可删除）"""
    try:
        from dao.group_chat_dao import GroupChatDAO, GroupMemoryDAO

        # 检查权限（只有群创建者能删除记忆）
        group = await GroupChatDAO.get(db, group_id)
        if not group or group.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有群创建者能管理群记忆",
            )

        # 删除记忆
        await GroupMemoryDAO.delete(db, memory_id)
        await db.commit()

        return {"ok": True, "message": "记忆已删除"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )



@router.get("/groups/{group_id}/souls/{soul_id}/memories")
async def get_group_memories(
    group_id: int,
    soul_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取群记忆（仅群成员可查看）"""
    try:
        from dao.group_chat_dao import GroupChatDAO, GroupMemberDAO, GroupMemoryDAO

        # 检查权限（成员可查看）
        is_member = await GroupMemberDAO.is_member(db, group_id, user.id)
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="你不是这个群的成员",
            )

        # 获取记忆
        memories = await GroupMemoryDAO.get_by_group_soul(db, group_id, soul_id)

        return {
            "memories": [
                {
                    "id": m.id,
                    "memory_type": m.memory_type,
                    "content": m.content,
                    "created_at": m.created_at.isoformat(),
                }
                for m in memories
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
