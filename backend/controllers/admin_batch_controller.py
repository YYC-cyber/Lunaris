"""
后台管理 - 批量操作 API 控制器（P2-08）
- 批量删除用户
- 批量暂停用户账户
- 批量删除消息
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from pydantic import BaseModel
import uuid

from config.database import get_db
from middleware.auth_middleware import get_current_user, is_admin_user
from models.user import User
from models.message import Message

router = APIRouter()

# ===== Pydantic 模型 =====
class BatchDeleteRequest(BaseModel):
    user_ids: list[uuid.UUID]

class BatchSuspendRequest(BaseModel):
    user_ids: list[uuid.UUID]
    duration_days: int

class BatchMessageDeleteRequest(BaseModel):
    message_ids: list[int]

class BatchOperationResponse(BaseModel):
    deleted_count: int | None = None
    suspended_count: int | None = None

# ===== 权限检查 =====
async def check_admin(user: User = Depends(get_current_user)):
    """检查用户是否为管理员"""
    if not is_admin_user(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以访问"
        )
    return user

# ===== 批量删除用户 =====
@router.post("/users/batch-delete", dependencies=[Depends(check_admin)])
async def batch_delete_users(
    request: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db)
):
    """批量删除用户（包括关联数据）"""
    if len(request.user_ids) > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="单次操作最多删除 1000 个用户"
        )

    if not request.user_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户 ID 列表不能为空"
        )

    try:
        # 删除用户（级联删除消息、好友关系等）
        result = await db.execute(
            delete(User).where(User.id.in_(request.user_ids))
        )
        await db.commit()
        deleted_count = result.rowcount or 0

        return {
            "deleted_count": deleted_count,
            "message": f"成功删除 {deleted_count} 个用户"
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除用户失败: {str(e)}"
        )

# ===== 批量暂停用户账户 =====
@router.post("/users/batch-suspend", dependencies=[Depends(check_admin)])
async def batch_suspend_users(
    request: BatchSuspendRequest,
    db: AsyncSession = Depends(get_db)
):
    """批量暂停用户账户"""
    if len(request.user_ids) > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="单次操作最多暂停 1000 个用户"
        )

    if not request.user_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户 ID 列表不能为空"
        )

    if request.duration_days <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="暂停天数必须大于 0"
        )

    try:
        # 计算暂停截止时间
        suspended_until = datetime.now() + timedelta(days=request.duration_days)

        # 查询用户并更新暂停时间
        stmt = select(User).where(User.id.in_(request.user_ids))
        result = await db.execute(stmt)
        users = result.scalars().all()

        suspended_count = 0
        for user in users:
            user.suspended_until = suspended_until
            suspended_count += 1

        await db.commit()

        return {
            "suspended_count": suspended_count,
            "suspended_until": suspended_until.isoformat(),
            "message": f"成功暂停 {suspended_count} 个用户账户，有效期至 {suspended_until.isoformat()}"
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"暂停用户失败: {str(e)}"
        )

# ===== 批量删除消息 =====
@router.post("/messages/batch-delete", dependencies=[Depends(check_admin)])
async def batch_delete_messages(
    request: BatchMessageDeleteRequest,
    db: AsyncSession = Depends(get_db)
):
    """批量删除消息"""
    if len(request.message_ids) > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="单次操作最多删除 1000 条消息"
        )

    if not request.message_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="消息 ID 列表不能为空"
        )

    try:
        # 删除消息
        result = await db.execute(
            delete(Message).where(Message.id.in_(request.message_ids))
        )
        await db.commit()
        deleted_count = result.rowcount or 0

        return {
            "deleted_count": deleted_count,
            "message": f"成功删除 {deleted_count} 条消息"
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除消息失败: {str(e)}"
        )
