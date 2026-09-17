"""群组权限数据访问层"""
from datetime import datetime
from typing import List, Optional, Dict

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.v1_0.group_permission import GroupPermission


class GroupPermissionDAO:
    """群组权限 DAO"""

    @staticmethod
    async def get_permissions(
        db: AsyncSession,
        group_id: int,
        role: str,
    ) -> Optional[GroupPermission]:
        """获取指定角色的权限配置"""
        stmt = select(GroupPermission).where(
            GroupPermission.group_id == group_id,
            GroupPermission.role == role,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_all_permissions(
        db: AsyncSession,
        group_id: int,
    ) -> List[GroupPermission]:
        """获取群组所有角色的权限配置"""
        stmt = select(GroupPermission).where(
            GroupPermission.group_id == group_id,
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def update_permissions(
        db: AsyncSession,
        group_id: int,
        role: str,
        permission_dict: Dict[str, bool],
    ) -> GroupPermission:
        """更新指定角色的权限"""
        perm = await GroupPermissionDAO.get_permissions(db, group_id, role)

        if not perm:
            perm = GroupPermission(
                group_id=group_id,
                role=role,
            )
            db.add(perm)

        for key, value in permission_dict.items():
            if hasattr(perm, key):
                setattr(perm, key, value)

        await db.flush()
        return perm

    @staticmethod
    async def check_permission(
        db: AsyncSession,
        group_id: int,
        role: str,
        action: str,
    ) -> bool:
        """检查指定角色是否有某个权限"""
        perm = await GroupPermissionDAO.get_permissions(db, group_id, role)

        if not perm:
            return False

        permission_map = {
            "invite": "can_invite",
            "kick": "can_kick",
            "edit_info": "can_edit_info",
            "delete_messages": "can_delete_messages",
            "pin": "can_pin",
            "manage_roles": "can_manage_roles",
        }

        perm_attr = permission_map.get(action)
        if not perm_attr:
            return False

        return getattr(perm, perm_attr, False)
