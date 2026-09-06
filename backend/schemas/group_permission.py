"""群组权限 Schema"""
from typing import Dict, List

from pydantic import BaseModel


class GroupPermissionOut(BaseModel):
    """单个角色权限信息"""
    id: int
    group_id: int
    role: str
    can_invite: bool
    can_kick: bool
    can_edit_info: bool
    can_delete_messages: bool
    can_pin: bool
    can_manage_roles: bool
    created_at: str


class GroupPermissionsListOut(BaseModel):
    """权限列表"""
    permissions: List[GroupPermissionOut]


class UpdatePermissionsRequest(BaseModel):
    """更新权限请求"""
    can_invite: bool | None = None
    can_kick: bool | None = None
    can_edit_info: bool | None = None
    can_delete_messages: bool | None = None
    can_pin: bool | None = None
    can_manage_roles: bool | None = None
