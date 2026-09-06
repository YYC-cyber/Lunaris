"""群组权限服务"""
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from dao.group_permission_dao import GroupPermissionDAO
from models.group_permission import GroupPermission


class GroupPermissionService:
    """群组权限服务"""

    @staticmethod
    async def get_permissions(
        db: AsyncSession,
        group_id: int,
        role: str,
    ) -> Optional[GroupPermission]:
        """获取指定角色的权限配置"""
        return await GroupPermissionDAO.get_permissions(db, group_id, role)

    @staticmethod
    async def list_all_permissions(
        db: AsyncSession,
        group_id: int,
    ) -> List[GroupPermission]:
        """获取群组所有角色的权限配置"""
        return await GroupPermissionDAO.list_all_permissions(db, group_id)

    @staticmethod
    async def update_permissions(
        db: AsyncSession,
        group_id: int,
        role: str,
        permission_dict: Dict[str, bool],
    ) -> GroupPermission:
        """更新指定角色的权限"""
        return await GroupPermissionDAO.update_permissions(db, group_id, role, permission_dict)

    @staticmethod
    async def check_permission(
        db: AsyncSession,
        group_id: int,
        role: str,
        action: str,
    ) -> bool:
        """检查指定角色是否有某个权限"""
        return await GroupPermissionDAO.check_permission(db, group_id, role, action)
