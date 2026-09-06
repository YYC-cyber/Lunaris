"""群组权限控制器"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from middleware.auth_middleware import get_current_user
from models.user import User
from services.group_permission_service import GroupPermissionService
from services.group_chat_service import GroupChatService
from dao.group_chat_dao import GroupMemberDAO
from schemas.group_permission import (
    GroupPermissionOut,
    GroupPermissionsListOut,
    UpdatePermissionsRequest,
)

router = APIRouter()


@router.get("/groups/{group_id}/permissions")
async def list_permissions(
    group_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GroupPermissionsListOut:
    """获取群组所有角色的权限配置"""
    # 检查群聊是否存在
    group_info = await GroupChatService.get_group_info(db, group_id)
    if not group_info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="群聊不存在")

    # 检查用户是否是群成员
    is_member = await GroupMemberDAO.is_member(db, group_id, user.id)
    if not is_member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="你不是群成员")

    # 获取所有权限配置
    permissions = await GroupPermissionService.list_all_permissions(db, group_id)

    permission_list = [
        GroupPermissionOut(
            id=perm.id,
            group_id=perm.group_id,
            role=perm.role,
            can_invite=perm.can_invite,
            can_kick=perm.can_kick,
            can_edit_info=perm.can_edit_info,
            can_delete_messages=perm.can_delete_messages,
            can_pin=perm.can_pin,
            can_manage_roles=perm.can_manage_roles,
            created_at=perm.created_at.isoformat(),
        )
        for perm in permissions
    ]

    return GroupPermissionsListOut(permissions=permission_list)


@router.patch("/groups/{group_id}/permissions/{role}")
async def update_permissions(
    group_id: int,
    role: str,
    req: UpdatePermissionsRequest,
    operator: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GroupPermissionOut:
    """更新指定角色的权限（仅群主可操作）"""
    # 检查群聊是否存在
    group_info = await GroupChatService.get_group_info(db, group_id)
    if not group_info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="群聊不存在")

    # 检查操作者是否是群主
    if group_info.get("creator_id") != str(operator.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅群主可修改权限")

    # 验证角色名称
    valid_roles = ["owner", "admin", "member", "guest"]
    if role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的角色，必须为：{', '.join(valid_roles)}",
        )

    # 构建权限字典（只更新非 None 的字段）
    permission_dict = {}
    if req.can_invite is not None:
        permission_dict["can_invite"] = req.can_invite
    if req.can_kick is not None:
        permission_dict["can_kick"] = req.can_kick
    if req.can_edit_info is not None:
        permission_dict["can_edit_info"] = req.can_edit_info
    if req.can_delete_messages is not None:
        permission_dict["can_delete_messages"] = req.can_delete_messages
    if req.can_pin is not None:
        permission_dict["can_pin"] = req.can_pin
    if req.can_manage_roles is not None:
        permission_dict["can_manage_roles"] = req.can_manage_roles

    # 更新权限
    perm = await GroupPermissionService.update_permissions(db, group_id, role, permission_dict)
    await db.commit()

    return GroupPermissionOut(
        id=perm.id,
        group_id=perm.group_id,
        role=perm.role,
        can_invite=perm.can_invite,
        can_kick=perm.can_kick,
        can_edit_info=perm.can_edit_info,
        can_delete_messages=perm.can_delete_messages,
        can_pin=perm.can_pin,
        can_manage_roles=perm.can_manage_roles,
        created_at=perm.created_at.isoformat(),
    )
