# backend/controllers/moment_controller.py
"""朋友圈路由。当前用户身份来自 JWT token（get_current_user）。"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from middleware.auth_middleware import get_current_user
from models.user import User
from services.moment_service import MomentService
from schemas.moment import MomentPublishIn, MomentVisibilityIn

router = APIRouter()


class CommentIn(BaseModel):
    content: str = Field(..., min_length=1, max_length=500)
    parent_comment_id: int | None = None


@router.post("")
async def publish_moment(
    data: MomentPublishIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """发布新朋友圈动态"""
    try:
        moment = await MomentService.publish(
            db,
            user_id=user.id,
            content=data.content,
            images=data.images,
            topic_tags=data.topic_tags,
            visibility=data.visibility,
            visible_groups=data.visible_groups,
            hidden_user_ids=[str(uid) for uid in data.hidden_user_ids],
        )
        await db.commit()
        return {
            "id": moment.id,
            "content": moment.content,
            "images": moment.images or [],
            "visibility": moment.visibility,
            "visible_groups": moment.visible_groups or [],
            "hidden_user_ids": moment.hidden_user_ids or [],
            "created_at": moment.created_at.isoformat(),
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"发布失败: {str(e)}")


@router.delete("/{moment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_moment(
    moment_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除自己的朋友圈动态"""
    success = await MomentService.delete_moment(db, moment_id, user.id)
    if not success:
        raise HTTPException(status_code=404, detail="动态不存在或无权删除")
    await db.commit()


@router.patch("/{moment_id}/visibility")
async def update_moment_visibility(
    moment_id: int,
    data: MomentVisibilityIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新朋友圈动态隐私设置"""
    moment = await MomentService.update_visibility(
        db, moment_id, user.id, data.visibility,
        visible_groups=data.visible_groups,
        hidden_user_ids=[str(uid) for uid in data.hidden_user_ids],
    )
    if not moment:
        raise HTTPException(status_code=404, detail="动态不存在或无权修改")
    await db.commit()
    return {
        "id": moment.id,
        "visibility": moment.visibility,
        "visible_groups": moment.visible_groups or [],
        "hidden_user_ids": moment.hidden_user_ids or [],
    }


@router.get("")
async def get_timeline(
    user: User = Depends(get_current_user),
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """朋友圈时间线（含点赞状态与评论）。"""
    moments = await MomentService.get_timeline(db, user.id, limit, offset)
    return {"data": moments, "total": len(moments)}


@router.post("/{moment_id}/like")
async def toggle_like(
    moment_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """点赞 / 取消点赞。"""
    is_liked = await MomentService.toggle_like(db, moment_id, user.id)
    return {"is_liked": is_liked}


@router.post("/{moment_id}/comment")
async def add_comment(
    moment_id: int,
    data: CommentIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """评论动态（触发 AI 评论区楼中楼回复）。"""
    comment = await MomentService.add_comment(
        db=db,
        moment_id=moment_id,
        user_id=user.id,
        content=data.content,
        parent_comment_id=data.parent_comment_id,
    )
    return {
        "id": comment.id,
        "content": comment.content,
        "created_at": comment.created_at.isoformat(),
        "is_ai": False,
    }
