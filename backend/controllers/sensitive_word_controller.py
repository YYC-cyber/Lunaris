"""
敏感词管理控制器 —— 管理员专用

支持敏感词的增删改查和统计
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from common import success
from config.database import get_db
from middleware.auth_middleware import get_current_user, is_admin_user
from models.user import User
from services.sensitive_word_service import SensitiveWordService
from schemas.sensitive_word import (
    SensitiveWordCreateRequest, SensitiveWordUpdateRequest,
    SensitiveWordOut, SensitiveWordListOut, SensitiveWordStatsOut
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/api/admin/sensitive-words")
async def add_sensitive_word(
    data: SensitiveWordCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    添加敏感词

    【管理员专用】

    添加新的敏感词到数据库
    """
    if not is_admin_user(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，仅管理员可访问"
        )

    try:
        sensitive_word = await SensitiveWordService.add_word(
            db,
            word=data.word,
            category=data.category,
            created_by=user.id,
            effective_at=data.effective_at,
            expires_at=data.expires_at,
        )

        logger.info(
            f"敏感词已添加: word={data.word}, "
            f"category={data.category}, created_by={user.id}"
        )

        return success(
            data=SensitiveWordOut.model_validate(sensitive_word),
            message="敏感词已添加"
        )

    except Exception as e:
        logger.error(f"添加敏感词失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="操作失败，请稍后重试"
        )


@router.delete("/api/admin/sensitive-words/{word}")
async def delete_sensitive_word(
    word: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    删除敏感词

    【管理员专用】

    软删除敏感词（设置 is_active=false）
    """
    if not is_admin_user(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )

    try:
        success_flag = await SensitiveWordService.remove_word(db, word)

        if not success_flag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="敏感词不存在"
            )

        logger.info(f"敏感词已删除: word={word}, deleted_by={user.id}")

        return success(message="敏感词已删除")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除敏感词失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="操作失败，请稍后重试"
        )


@router.get("/api/admin/sensitive-words")
async def list_sensitive_words(
    category: str = Query(None, description="分类过滤"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    列表敏感词

    【管理员专用】

    查看敏感词列表，支持分类过滤和分页
    """
    if not is_admin_user(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )

    try:
        from dao.sensitive_word_dao import SensitiveWordDAO
        words = await SensitiveWordDAO.list_active(
            db, limit=limit, offset=offset, category=category
        )
        # 获取总数（不分页）
        from sqlalchemy import select, func
        stmt = select(func.count()).select_from(SensitiveWordDAO.model)
        if category:
            from models.sensitive_word import SensitiveWord
            stmt = stmt.where(SensitiveWord.category == category)
        total = (await db.execute(stmt)).scalar_one()

        return success(
            data=SensitiveWordListOut(
                total=total,
                words=[SensitiveWordOut.model_validate(w) for w in words]
            )
        )

    except Exception as e:
        logger.error(f"获取敏感词列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取失败，请稍后重试"
        )


@router.patch("/api/admin/sensitive-words/{word}")
async def update_sensitive_word(
    word: str,
    data: SensitiveWordUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    更新敏感词

    【管理员专用】

    更新敏感词的状态、分类或过期时间
    """
    if not is_admin_user(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )

    try:
        sensitive_word = await SensitiveWordService.update_word(
            db,
            word,
            is_active=data.is_active,
            category=data.category,
            expires_at=data.expires_at,
        )

        if not sensitive_word:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="敏感词不存在"
            )

        logger.info(f"敏感词已更新: word={word}, updated_by={user.id}")

        return success(
            data=SensitiveWordOut.model_validate(sensitive_word),
            message="敏感词已更新"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新敏感词失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="操作失败，请稍后重试"
        )


@router.get("/api/admin/sensitive-words/stats")
async def get_sensitive_word_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    敏感词统计

    【管理员专用】

    显示敏感词统计信息（按分类）
    """
    if not is_admin_user(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )

    try:
        stats = await SensitiveWordService.get_stats(db)
        return success(data=SensitiveWordStatsOut(**stats))

    except Exception as e:
        logger.error(f"获取统计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取失败，请稍后重试"
        )
