"""群聊数据访问层"""
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from models.v1_0.group_chat import GroupChat, GroupMember, GroupMessage, GroupInvitation, GroupMemory, MemberTypeEnum


class GroupChatDAO:
    """群聊 DAO"""

    @staticmethod
    async def create(
        db: AsyncSession,
        user_id: uuid.UUID,
        group_name: str,
        group_type: str,
        auto_delete_hours: Optional[int] = None,
    ) -> GroupChat:
        """创建群聊"""
        group = GroupChat(
            user_id=user_id,
            group_name=group_name,
            group_type=group_type,
            auto_delete_hours=auto_delete_hours,
        )
        db.add(group)
        await db.flush()
        return group

    @staticmethod
    async def get(db: AsyncSession, group_id: int) -> Optional[GroupChat]:
        """获取群聊"""
        stmt = select(GroupChat).where(GroupChat.id == group_id, GroupChat.is_deleted == False)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_by_user(db: AsyncSession, user_id: uuid.UUID) -> List[GroupChat]:
        """获取用户的所有群聊"""
        stmt = (
            select(GroupChat)
            .join(GroupMember, GroupMember.group_id == GroupChat.id)
            .where(
                GroupMember.member_id == user_id,
                GroupMember.status == "active",
                GroupChat.is_deleted == False,
            )
            .order_by(desc(GroupChat.updated_at))
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def update(db: AsyncSession, group: GroupChat, **kwargs) -> GroupChat:
        """更新群聊"""
        for key, value in kwargs.items():
            setattr(group, key, value)
        group.updated_at = datetime.now()
        await db.flush()
        return group

    @staticmethod
    async def delete(db: AsyncSession, group_id: int) -> None:
        """软删除群聊"""
        group = await GroupChatDAO.get(db, group_id)
        if group:
            group.is_deleted = True
            await db.flush()


class GroupMemberDAO:
    """群成员 DAO"""

    @staticmethod
    async def add_member(
        db: AsyncSession,
        group_id: int,
        member_type: str,
        member_id: Optional[uuid.UUID] = None,
        soul_id: Optional[int] = None,
        role: str = "member",
    ) -> GroupMember:
        """添加成员"""
        member = GroupMember(
            group_id=group_id,
            member_type=member_type,
            member_id=member_id if member_type == "human" else None,
            soul_id=soul_id if member_type == "ai" else None,
            role=role,
        )
        db.add(member)
        await db.flush()
        return member

    @staticmethod
    async def get_members(db: AsyncSession, group_id: int, status: str = "active") -> List[GroupMember]:
        """获取群成员"""
        stmt = select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.status == status,
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get(db: AsyncSession, member_id: int) -> Optional[GroupMember]:
        result = await db.execute(select(GroupMember).where(GroupMember.id == member_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def is_member(db: AsyncSession, group_id: int, user_id: uuid.UUID) -> bool:
        """检查是否是成员"""
        stmt = select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.member_id == user_id,
            GroupMember.status == "active",
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def remove_member(db: AsyncSession, group_id: int, member_id: int) -> None:
        """按群成员记录 ID 移除成员。"""
        stmt = select(GroupMember).where(
            GroupMember.id == member_id,
            GroupMember.group_id == group_id,
        )
        result = await db.execute(stmt)
        member = result.scalar_one_or_none()
        if member:
            await db.delete(member)
            await db.flush()


class GroupMessageDAO:
    """群消息 DAO"""

    @staticmethod
    async def create(
        db: AsyncSession,
        group_id: int,
        sender_type: str,
        content: str,
        sender_id: Optional[uuid.UUID] = None,
        soul_id: Optional[int] = None,
        voice_url: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> GroupMessage:
        """创建消息"""
        message = GroupMessage(
            group_id=group_id,
            sender_type=sender_type,
            content=content,
            sender_id=sender_id if sender_type == "user" else None,
            soul_id=soul_id if sender_type == "ai" else None,
            voice_url=voice_url,
            expires_at=expires_at,
        )
        db.add(message)
        await db.flush()
        return message

    @staticmethod
    async def list_messages(
        db: AsyncSession,
        group_id: int,
        limit: int = 50,
    ) -> List[GroupMessage]:
        """获取群消息（包括已过期的消息，用于显示占位符）"""
        stmt = (
            select(GroupMessage)
            .where(GroupMessage.group_id == group_id)
            .order_by(desc(GroupMessage.created_at))
            .limit(limit)
        )
        result = await db.execute(stmt)
        messages = result.scalars().all()
        messages.reverse()  # 正序返回
        return messages

    @staticmethod
    async def update(db: AsyncSession, message: GroupMessage, **kwargs) -> GroupMessage:
        """更新消息"""
        for key, value in kwargs.items():
            setattr(message, key, value)
        await db.flush()
        return message

    @staticmethod
    async def delete(db: AsyncSession, message_id: int) -> None:
        """软删除消息"""
        stmt = select(GroupMessage).where(GroupMessage.id == message_id)
        result = await db.execute(stmt)
        message = result.scalar_one_or_none()
        if message:
            message.is_deleted = True
            await db.flush()


class GroupInvitationDAO:
    """群邀请 DAO"""

    @staticmethod
    async def create(
        db: AsyncSession,
        group_id: int,
        inviter_id: uuid.UUID,
        invitee_id: uuid.UUID,
        expires_at: Optional[datetime] = None,
    ) -> GroupInvitation:
        """创建邀请"""
        if expires_at is None:
            expires_at = datetime.now() + timedelta(hours=24)

        invitation = GroupInvitation(
            group_id=group_id,
            inviter_id=inviter_id,
            invitee_id=invitee_id,
            expires_at=expires_at,
        )
        db.add(invitation)
        await db.flush()
        return invitation

    @staticmethod
    async def get(db: AsyncSession, invitation_id: int) -> Optional[GroupInvitation]:
        """获取邀请"""
        stmt = select(GroupInvitation).where(GroupInvitation.id == invitation_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_pending_invitations(db: AsyncSession, invitee_id: uuid.UUID) -> List[GroupInvitation]:
        """获取待处理的邀请"""
        from models.v1_0.group_chat import InvitationStatusEnum
        stmt = (
            select(GroupInvitation)
            .where(
                GroupInvitation.invitee_id == invitee_id,
                GroupInvitation.status == InvitationStatusEnum.PENDING,
                GroupInvitation.expires_at > datetime.now(),
            )
            .order_by(desc(GroupInvitation.created_at))
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def update_status(
        db: AsyncSession,
        invitation_id: int,
        status: str,
    ) -> Optional[GroupInvitation]:
        """更新邀请状态"""
        invitation = await GroupInvitationDAO.get(db, invitation_id)
        if invitation:
            invitation.status = status
            await db.flush()
        return invitation


class GroupMemoryDAO:
    """群记忆 DAO"""

    @staticmethod
    async def create(
        db: AsyncSession,
        group_id: int,
        soul_id: int,
        memory_type: str,
        content: str,
    ) -> GroupMemory:
        """创建群记忆"""
        memory = GroupMemory(
            group_id=group_id,
            soul_id=soul_id,
            memory_type=memory_type,
            content=content,
        )
        db.add(memory)
        await db.flush()
        return memory

    @staticmethod
    async def get_by_group_soul(
        db: AsyncSession,
        group_id: int,
        soul_id: int,
    ) -> List[GroupMemory]:
        """获取群内某个 AI 的所有记忆"""
        stmt = select(GroupMemory).where(
            GroupMemory.group_id == group_id,
            GroupMemory.soul_id == soul_id,
            GroupMemory.is_deleted == False,
        ).order_by(desc(GroupMemory.created_at))
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def delete(db: AsyncSession, memory_id: int) -> None:
        """软删除记忆"""
        stmt = select(GroupMemory).where(GroupMemory.id == memory_id)
        result = await db.execute(stmt)
        memory = result.scalar_one_or_none()
        if memory:
            memory.is_deleted = True
            await db.flush()
