"""群聊服务"""
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from dao.v1_0.group_chat_dao import GroupChatDAO, GroupMemberDAO, GroupMessageDAO, GroupInvitationDAO
from dao.v1_0.soul_dao import SoulDAO
from dao.user_dao import UserDAO
from models.v1_0.group_chat import GroupTypeEnum, MemberTypeEnum


class GroupChatService:
    """群聊服务"""

    @staticmethod
    async def create_group(
        db: AsyncSession,
        user_id: uuid.UUID,
        group_name: str,
        group_type: str,
        ai_soul_ids: Optional[List[int]] = None,
        human_user_ids: Optional[List[uuid.UUID]] = None,
        auto_delete_hours: Optional[int] = None,
    ) -> Dict:
        """创建群聊并添加成员"""
        # 创建群聊
        group = await GroupChatDAO.create(
            db,
            user_id=user_id,
            group_name=group_name,
            group_type=group_type,
            auto_delete_hours=auto_delete_hours,
        )

        # 添加创建者为成员
        await GroupMemberDAO.add_member(
            db,
            group_id=group.id,
            member_type="human",
            member_id=user_id,
            role="owner",
        )

        # 添加 AI 成员
        if ai_soul_ids:
            for soul_id in ai_soul_ids:
                await GroupMemberDAO.add_member(
                    db,
                    group_id=group.id,
                    member_type="ai",
                    soul_id=soul_id,
                    role="member",
                )

        # 添加真人成员（邀请）
        if human_user_ids:
            for human_user_id in human_user_ids:
                if human_user_id != user_id:  # 不邀请自己
                    await GroupInvitationDAO.create(
                        db,
                        group_id=group.id,
                        inviter_id=user_id,
                        invitee_id=human_user_id,
                    )

        await db.commit()
        return await GroupChatService.get_group_info(db, group.id)

    @staticmethod
    async def get_group_info(db: AsyncSession, group_id: int) -> Dict:
        """获取群聊详情"""
        group = await GroupChatDAO.get(db, group_id)
        if not group:
            return None

        members = await GroupMemberDAO.get_members(db, group_id)
        member_list = []

        for member in members:
            if member.member_type == "ai":
                soul = await SoulDAO.get(db, member.soul_id)
                member_list.append({
                    "id": member.id,
                    "type": "ai",
                    "name": soul.display_name if soul else "Unknown",
                    "soul_id": member.soul_id,
                    "role": member.role,
                })
            else:
                user = await UserDAO.get(db, member.member_id)
                member_list.append({
                    "id": member.id,
                    "type": "human",
                    "name": user.nickname if user else "Unknown",
                    "user_id": str(member.member_id),
                    "role": member.role,
                })

        return {
            "id": group.id,
            "name": group.group_name,
            "type": group.group_type,
            "creator_id": str(group.user_id),
            "created_at": group.created_at.isoformat(),
            "auto_delete_hours": group.auto_delete_hours,
            "announcement": group.announcement,
            "members": member_list,
        }

    @staticmethod
    async def send_message(
        db: AsyncSession,
        group_id: int,
        sender_type: str,
        content: str,
        sender_id: Optional[uuid.UUID] = None,
        soul_id: Optional[int] = None,
        voice_url: Optional[str] = None,
    ) -> Dict:
        """发送群消息"""
        group = await GroupChatDAO.get(db, group_id)
        if not group:
            raise ValueError("群聊不存在")

        # 检查发送者是否被禁言（仅对真人发送者检查）
        if sender_type == "user" and sender_id:
            from services.v1_0.group_mute_service import GroupMuteService
            mute = await GroupMuteService.get_active_mute(db, group_id, sender_id)
            if mute:
                raise PermissionError(f"你在该群组已被禁言，禁言截止时间为：{mute.muted_until.isoformat()}")

        # 计算过期时间
        expires_at = None
        if group.auto_delete_hours:
            expires_at = datetime.now() + timedelta(hours=group.auto_delete_hours)

        # 创建消息
        message = await GroupMessageDAO.create(
            db,
            group_id=group_id,
            sender_type=sender_type,
            content=content,
            sender_id=sender_id,
            soul_id=soul_id,
            voice_url=voice_url,
            expires_at=expires_at,
        )

        # 更新群聊时间
        await GroupChatDAO.update(db, group, updated_at=datetime.now())

        await db.commit()

        if sender_type == "ai":
            soul = await SoulDAO.get(db, soul_id) if soul_id else None
            sender_name = soul.display_name if soul else "Unknown"
            public_sender_id = str(soul_id) if soul_id is not None else ""
        else:
            user = await UserDAO.get(db, sender_id) if sender_id else None
            sender_name = (user.nickname or user.username) if user else "Unknown"
            public_sender_id = str(sender_id) if sender_id else ""

        return {
            "id": message.id,
            "group_id": group_id,
            "sender_type": sender_type,
            "sender_name": sender_name,
            "sender_id": public_sender_id,
            "content": content,
            "voice_url": voice_url,
            "created_at": message.created_at.isoformat(),
            "is_deleted": message.is_deleted,
            "expires_at": message.expires_at.isoformat() if message.expires_at else None,
        }

    @staticmethod
    async def get_message_history(
        db: AsyncSession,
        group_id: int,
        limit: int = 50,
    ) -> List[Dict]:
        """获取群聊消息历史（过期消息显示为占位符）"""
        messages = await GroupMessageDAO.list_messages(db, group_id, limit=limit)

        result = []
        for msg in messages:
            if msg.sender_type == "ai":
                soul = await SoulDAO.get(db, msg.soul_id)
                sender_name = soul.display_name if soul else "Unknown"
            else:
                user = await UserDAO.get(db, msg.sender_id)
                sender_name = (user.nickname or user.username) if user else "Unknown"

            # 判断消息显示内容
            if msg.is_deleted:
                display_content = "[消息已删除]"
            elif msg.expires_at and msg.expires_at <= datetime.now():
                display_content = "[消息已过期]"
            else:
                display_content = msg.content

            result.append({
                "id": msg.id,
                "group_id": group_id,
                "sender_type": msg.sender_type,
                "sender_name": sender_name,
                "sender_id": str(msg.sender_id) if msg.sender_type == "user" else str(msg.soul_id),
                "content": display_content,
                "voice_url": msg.voice_url,
                "created_at": msg.created_at.isoformat(),
                "is_deleted": msg.is_deleted,
                "expires_at": msg.expires_at.isoformat() if msg.expires_at else None,
            })

        return result

    @staticmethod
    async def invite_member(
        db: AsyncSession,
        group_id: int,
        inviter_id: uuid.UUID,
        invitee_id: uuid.UUID,
    ) -> Dict:
        """邀请成员加入群聊"""
        group = await GroupChatDAO.get(db, group_id)
        if not group:
            raise ValueError("群聊不存在")

        # 检查权限（只有创建者能邀请）
        if group.user_id != inviter_id:
            raise PermissionError("只有群创建者能邀请成员")

        # 检查是否已经是成员
        is_member = await GroupMemberDAO.is_member(db, group_id, invitee_id)
        if is_member:
            raise ValueError("该用户已经是群成员")

        # 创建邀请
        invitation = await GroupInvitationDAO.create(
            db,
            group_id=group_id,
            inviter_id=inviter_id,
            invitee_id=invitee_id,
        )

        await db.commit()

        return {
            "id": invitation.id,
            "group_id": group_id,
            "inviter_id": str(inviter_id),
            "invitee_id": str(invitee_id),
            "status": invitation.status,
            "created_at": invitation.created_at.isoformat(),
            "expires_at": invitation.expires_at.isoformat(),
        }

    @staticmethod
    async def add_member(
        db: AsyncSession,
        group_id: int,
        operator_id: uuid.UUID,
        member_type: str,
        member_id: Optional[uuid.UUID] = None,
        soul_id: Optional[int] = None,
    ) -> Dict:
        group = await GroupChatDAO.get(db, group_id)
        if not group:
            raise ValueError("群聊不存在")
        if not await GroupChatService._can_manage_members(db, group_id, operator_id):
            raise PermissionError("只有群主或管理员可以管理成员")
        if member_type not in {"human", "ai"}:
            raise ValueError("成员类型不正确")
        if member_type == "human" and not member_id:
            raise ValueError("缺少用户 ID")
        if member_type == "ai" and not soul_id:
            raise ValueError("缺少 AI 角色 ID")
        if member_type == "human" and await GroupMemberDAO.is_member(db, group_id, member_id):
            raise ValueError("该用户已经是群成员")

        member = await GroupMemberDAO.add_member(
            db, group_id, member_type, member_id=member_id, soul_id=soul_id, role="member"
        )
        return {
            "id": member.id,
            "group_id": group_id,
            "type": member_type,
            "soul_id": soul_id,
            "user_id": str(member_id) if member_id else None,
            "status": "active", "role": "member",
        }

    @staticmethod
    async def remove_member(
        db: AsyncSession,
        group_id: int,
        member_record_id: int,
        operator_id: uuid.UUID,
    ) -> None:
        group = await GroupChatDAO.get(db, group_id)
        if not group:
            raise ValueError("群聊不存在")
        if not await GroupChatService._can_manage_members(db, group_id, operator_id):
            raise PermissionError("只有群主或管理员可以管理成员")
        member = await GroupMemberDAO.get(db, member_record_id)
        if not member or member.group_id != group_id:
            raise ValueError("群成员不存在")
        if member.role == "owner":
            raise ValueError("不能移除群主")
        await GroupMemberDAO.remove_member(db, group_id, member_record_id)

    @staticmethod
    async def update_member(
        db: AsyncSession,
        group_id: int,
        member_record_id: int,
        operator_id: uuid.UUID,
        member_status: str,
    ) -> Dict:
        group = await GroupChatDAO.get(db, group_id)
        if not group:
            raise ValueError("群聊不存在")
        if group.user_id != operator_id:
            raise PermissionError("只有群主可以设置管理员")
        member = await GroupMemberDAO.get(db, member_record_id)
        if not member or member.group_id != group_id:
            raise ValueError("群成员不存在")
        if member.role == "owner":
            raise ValueError("不能修改群主角色")
        if member_status not in {"admin", "member"}:
            raise ValueError("成员角色不正确")
        member.role = member_status
        return {"id": member.id, "role": member_status}

    @staticmethod
    async def update_group_settings(
        db: AsyncSession,
        group_id: int,
        operator_id: uuid.UUID,
        group_name: Optional[str] = None,
        announcement: Optional[str] = None,
    ) -> Dict:
        group = await GroupChatDAO.get(db, group_id)
        if not group:
            raise ValueError("群聊不存在")
        if not await GroupChatService._can_manage_members(db, group_id, operator_id):
            raise PermissionError("只有群主或管理员可以修改群设置")
        updates = {}
        if group_name is not None:
            name = group_name.strip()
            if not name:
                raise ValueError("群名称不能为空")
            updates["group_name"] = name[:100]
        if announcement is not None:
            updates["announcement"] = announcement.strip()[:500] or None
        if updates:
            await GroupChatDAO.update(db, group, **updates)
        return await GroupChatService.get_group_info(db, group_id)

    @staticmethod
    async def _can_manage_members(db: AsyncSession, group_id: int, user_id: uuid.UUID) -> bool:
        group = await GroupChatDAO.get(db, group_id)
        if not group:
            return False
        if group.user_id == user_id:
            return True
        members = await GroupMemberDAO.get_members(db, group_id)
        return any(member.member_id == user_id and member.role == "admin" for member in members)

    @staticmethod
    async def leave_group(
        db: AsyncSession,
        group_id: int,
        user_id: uuid.UUID,
    ) -> None:
        """成员主动退出群聊"""
        group = await GroupChatDAO.get(db, group_id)
        if not group:
            raise ValueError("群聊不存在")

        # 检查用户是否是成员
        member = None
        members = await GroupMemberDAO.get_members(db, group_id, status="active")
        for m in members:
            if m.member_type == "human" and m.member_id == user_id:
                member = m
                break

        if not member:
            raise ValueError("你不是这个群的成员")

        # 群主不能直接退出（需要先转让权限）
        if member.role == "owner":
            raise ValueError("群主不能直接退出群聊，请先转让群主权限给其他成员")

        # 移除成员
        await GroupMemberDAO.remove_member(db, group_id, member.id)

    @staticmethod
    async def transfer_owner(
        db: AsyncSession,
        group_id: int,
        current_owner_id: uuid.UUID,
        new_owner_member_id: int,  # 新群主的 group_members 表记录 ID
    ) -> Dict:
        """转让群主权限"""
        group = await GroupChatDAO.get(db, group_id)
        if not group:
            raise ValueError("群聊不存在")

        if group.user_id != current_owner_id:
            raise PermissionError("只有当前群主可以转让权限")

        new_owner = await GroupMemberDAO.get(db, new_owner_member_id)
        if not new_owner or new_owner.group_id != group_id:
            raise ValueError("新群主不存在")

        if new_owner.member_type != "human":
            raise ValueError("只能转让给真人成员")

        # 更新权限
        current_owner_member = None
        members = await GroupMemberDAO.get_members(db, group_id, status="active")
        for m in members:
            if m.member_type == "human" and m.member_id == current_owner_id:
                current_owner_member = m
                break

        if current_owner_member:
            current_owner_member.role = "member"

        new_owner.role = "owner"
        await GroupChatDAO.update(db, group, user_id=new_owner.member_id)

        return {
            "group_id": group_id,
            "new_owner_id": str(new_owner.member_id),
            "old_owner_id": str(current_owner_id),
            "status": "success",
        }

    @staticmethod

    @staticmethod
    async def respond_to_invitation(
        db: AsyncSession,
        invitation_id: int,
        accept: bool,
    ) -> Dict:
        """响应邀请"""
        from models.v1_0.group_chat import InvitationStatusEnum

        invitation = await GroupInvitationDAO.get(db, invitation_id)
        if not invitation:
            raise ValueError("邀请不存在")

        if invitation.expires_at < datetime.now():
            raise ValueError("邀请已过期")

        if accept:
            # 添加为成员
            await GroupMemberDAO.add_member(
                db,
                group_id=invitation.group_id,
                member_type="human",
                member_id=invitation.invitee_id,
            )
            status = InvitationStatusEnum.ACCEPTED
        else:
            status = InvitationStatusEnum.DECLINED

        await GroupInvitationDAO.update_status(db, invitation_id, status)
        await db.commit()

        return {
            "id": invitation_id,
            "status": status.value,
        }

    @staticmethod
    def merge_consecutive_messages(messages: List[Dict], time_gap: int = 5) -> List[Dict]:
        """合并同一用户的连续消息（时间间隔 < time_gap 秒）"""
        if not messages:
            return messages

        merged = []
        current_group = []

        for msg in messages:
            if not current_group:
                current_group = [msg]
            elif (msg["sender_type"] == current_group[-1]["sender_type"] and
                  msg["sender_id"] == current_group[-1]["sender_id"] and
                  (datetime.fromisoformat(msg["created_at"]) -
                   datetime.fromisoformat(current_group[-1]["created_at"])).total_seconds() <= time_gap):
                # 加入当前组
                current_group.append(msg)
            else:
                # 提交当前组，开启新组
                if len(current_group) == 1:
                    merged.append(current_group[0])
                else:
                    merged.append(GroupChatService._merge_group(current_group))
                current_group = [msg]

        # 处理最后一组
        if current_group:
            if len(current_group) == 1:
                merged.append(current_group[0])
            else:
                merged.append(GroupChatService._merge_group(current_group))

        return merged

    @staticmethod
    def _merge_group(messages: List[Dict]) -> Dict:
        """将一组消息合并成一条"""
        content = "\n".join([m["content"] for m in messages])
        return {
            "id": messages[0]["id"],
            "group_id": messages[0]["group_id"],
            "sender_type": messages[0]["sender_type"],
            "sender_name": messages[0]["sender_name"],
            "sender_id": messages[0]["sender_id"],
            "content": content,
            "voice_url": messages[-1].get("voice_url"),
            "created_at": messages[0]["created_at"],
            "is_merged": True,
        }
