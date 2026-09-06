"""用户屏蔽控制器"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from common import success
from config.database import get_db
from middleware.auth_middleware import get_current_user
from models.user import User
from services.block_service import BlockService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/api/blocks/{user_id}")
async def block_user(
    user_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """屏蔽用户"""
    try:
        blocked_user_id = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的用户 ID"
        )

    try:
        await BlockService.block(db, user.id, blocked_user_id)
        await db.commit()
        logger.info(f"用户已屏蔽: blocker_id={user.id}, blocked_id={blocked_user_id}")
        return success(message="已屏蔽该用户")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"屏蔽用户失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="屏蔽失败，请稍后重试"
        )


@router.delete("/api/blocks/{user_id}")
async def unblock_user(
    user_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """取消屏蔽用户"""
    try:
        blocked_user_id = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的用户 ID"
        )

    try:
        await BlockService.unblock(db, user.id, blocked_user_id)
        await db.commit()
        logger.info(f"用户已取消屏蔽: blocker_id={user.id}, blocked_id={blocked_user_id}")
        return success(message="已取消屏蔽该用户")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"取消屏蔽失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="取消屏蔽失败，请稍后重试"
        )


@router.get("/api/blocks")
async def list_blocked_users(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):
    """获取屏蔽用户列表"""
    try:
        blocked_users = await BlockService.list_blocked(db, user.id, limit, offset)
        return success(
            data={
                "total": len(blocked_users),
                "blocked_users": blocked_users
            }
        )
    except Exception as e:
        logger.error(f"获取屏蔽列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取失败，请稍后重试"
        )
