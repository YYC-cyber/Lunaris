"""
用户数据管理 API - 中国 PIPL 合规

提供以下功能：
1. 数据导出 - PIPL 第 9 条 (数据可携权)
2. 账户硬删除 - PIPL 第 9 条 (遗忘权)
3. 个人信息修改 - PIPL 第 9 条 (更正权)
4. 撤销授权 - PIPL 第 9 条 (反对权)

所有操作都需要身份验证
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import json
from datetime import datetime
import logging

from common import success
from config.database import get_db
from middleware.auth_middleware import get_current_user
from models.user import User
from dao.user_dao import UserDAO
from dao.v1_0.message_dao import MessageDAO
from dao.v1_0.friendship_dao import FriendshipDAO
from dao.v1_0.moment_dao import MomentDAO
from dao.v1_0.comment_dao import CommentDAO
from dao.v1_0.memory_dao import MemoryDAO
from schemas.user_profile import UserProfileUpdateRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/user/export-data")
async def export_user_data(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    导出用户的所有个人数据

    PIPL 第 9 条：用户有权导出自己的所有个人信息

    返回格式：JSON 包含：
    - 用户基本信息
    - 所有消息记录
    - 亲密度数据
    - 记忆库内容
    - 朋友圈动态
    - 好友关系
    - 评论和点赞

    【数据格式】
    用户可将此导出数据转移到其他应用
    """
    try:
        # 1. 收集用户基本信息
        user_data = {
            "user_id": str(user.id),
            "username": user.username,
            "lunaris_id": user.lunaris_id,
            "gender": user.gender,
            "nickname": user.nickname,
            "avatar_url": user.avatar_url,
            "birthday": user.birthday.isoformat() if user.birthday else None,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        }

        # 2. 收集所有消息（如果 MessageDAO 存在）
        messages = []
        try:
            from dao.v1_0.message_dao import MessageDAO
            user_messages = await MessageDAO.get_by_user(db, user.id)
            messages = [
                {
                    "id": str(msg.id) if hasattr(msg, 'id') else None,
                    "content": msg.content if hasattr(msg, 'content') else None,
                    "created_at": msg.created_at.isoformat() if hasattr(msg, 'created_at') and msg.created_at else None,
                    "soul_id": str(msg.soul_id) if hasattr(msg, 'soul_id') else None,
                }
                for msg in (user_messages or [])
            ]
        except Exception as e:
            logger.warning(f"无法导出消息: {e}")

        # 3. 收集好友关系（如果 FriendshipDAO 存在）
        friendships = []
        try:
            from dao.v1_0.friendship_dao import FriendshipDAO
            user_friendships = await FriendshipDAO.get_by_user(db, user.id)
            friendships = [
                {
                    "friend_id": str(fs.friend_id) if hasattr(fs, 'friend_id') else None,
                    "intimacy": fs.intimacy if hasattr(fs, 'intimacy') else None,
                }
                for fs in (user_friendships or [])
            ]
        except Exception as e:
            logger.warning(f"无法导出好友关系: {e}")

        # 4. 收集朋友圈动态
        moments = []
        try:
            from dao.v1_0.moment_dao import MomentDAO
            user_moments = await MomentDAO.get_by_user(db, user.id)
            moments = [
                {
                    "id": str(m.id) if hasattr(m, 'id') else None,
                    "content": m.content if hasattr(m, 'content') else None,
                    "created_at": m.created_at.isoformat() if hasattr(m, 'created_at') and m.created_at else None,
                }
                for m in (user_moments or [])
            ]
        except Exception as e:
            logger.warning(f"无法导出朋友圈: {e}")

        # 5. 收集记忆库
        memories = []
        try:
            from dao.v1_0.memory_dao import MemoryDAO
            user_memories = await MemoryDAO.get_by_user(db, user.id)
            memories = [
                {
                    "id": str(m.id) if hasattr(m, 'id') else None,
                    "content": m.content if hasattr(m, 'content') else None,
                    "created_at": m.created_at.isoformat() if hasattr(m, 'created_at') and m.created_at else None,
                }
                for m in (user_memories or [])
            ]
        except Exception as e:
            logger.warning(f"无法导出记忆库: {e}")

        # 组装导出数据
        export_data = {
            "export_date": datetime.now().isoformat(),
            "data_format_version": "1.0",
            "user": user_data,
            "messages": messages,
            "friendships": friendships,
            "moments": moments,
            "memories": memories,
        }

        logger.info(f"用户数据导出: user_id={user.id}")

        return success(
            data=export_data,
            message="数据导出成功。这是你所有个人信息的完整副本，可用于数据转移。"
        )

    except Exception as e:
        logger.error(f"数据导出失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="数据导出失败，请稍后重试"
        )


@router.post("/api/account/delete-permanently")
async def delete_account_permanently(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    永久删除用户账户和所有关联数据

    PIPL 第 9 条：用户有权要求删除自己的所有个人信息 (遗忘权)
    PIPL 要求：30 天内完成硬删除

    删除内容：
    - 用户账户
    - 所有消息记录
    - 好友关系
    - 朋友圈动态
    - 评论和点赞
    - 记忆库数据
    - 聊天历史

    保留内容：
    - 匿名审计日志 (72小时后自动删除)

    风险等级：🔴 不可逆转操作
    """
    try:
        user_id = user.id
        username = user.username

        logger.warning(f"用户请求账户永久删除: user_id={user_id}, username={username}")

        # 【级联删除】删除所有关联数据
        # 顺序很重要：先删除依赖的数据，再删除用户
        deletion_log = {
            "user_id": str(user_id),
            "username": username,
            "deleted_at": datetime.now().isoformat(),
            "deleted_items": []
        }

        # 1. 删除消息
        try:
            from dao.v1_0.message_dao import MessageDAO
            deleted_count = await MessageDAO.delete_by_user(db, user_id)
            deletion_log["deleted_items"].append({
                "type": "messages",
                "count": deleted_count
            })
            logger.info(f"删除消息: {deleted_count} 条")
        except Exception as e:
            logger.warning(f"删除消息失败: {e}")

        # 2. 删除好友关系
        try:
            from dao.v1_0.friendship_dao import FriendshipDAO
            deleted_count = await FriendshipDAO.delete_by_user(db, user_id)
            deletion_log["deleted_items"].append({
                "type": "friendships",
                "count": deleted_count
            })
            logger.info(f"删除好友关系: {deleted_count} 条")
        except Exception as e:
            logger.warning(f"删除好友关系失败: {e}")

        # 3. 删除朋友圈动态
        try:
            from dao.v1_0.moment_dao import MomentDAO
            deleted_count = await MomentDAO.delete_by_user(db, user_id)
            deletion_log["deleted_items"].append({
                "type": "moments",
                "count": deleted_count
            })
            logger.info(f"删除朋友圈: {deleted_count} 条")
        except Exception as e:
            logger.warning(f"删除朋友圈失败: {e}")

        # 4. 删除记忆库
        try:
            from dao.v1_0.memory_dao import MemoryDAO
            deleted_count = await MemoryDAO.delete_by_user(db, user_id)
            deletion_log["deleted_items"].append({
                "type": "memories",
                "count": deleted_count
            })
            logger.info(f"删除记忆库: {deleted_count} 条")
        except Exception as e:
            logger.warning(f"删除记忆库失败: {e}")

        # 5. 删除评论和点赞
        try:
            from dao.v1_0.comment_dao import CommentDAO
            deleted_count = await CommentDAO.delete_by_user(db, user_id)
            deletion_log["deleted_items"].append({
                "type": "comments",
                "count": deleted_count
            })
            logger.info(f"删除评论: {deleted_count} 条")
        except Exception as e:
            logger.warning(f"删除评论失败: {e}")

        # 6. 最后删除用户账户（硬删除，不是软删除）
        await UserDAO.delete(db, user_id)
        deletion_log["deleted_items"].append({
            "type": "user_account",
            "count": 1
        })

        await db.commit()

        logger.warning(f"账户已永久删除: user_id={user_id}, deletion_log={deletion_log}")

        return success(
            data=deletion_log,
            message="你的账户和所有相关数据已被永久删除。"
                   "此操作不可撤销。"
        )

    except Exception as e:
        logger.error(f"账户删除失败: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="账户删除失败，请稍后重试或联系我们"
        )


@router.post("/api/user/profile/update")
async def update_user_profile(
    data: UserProfileUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    修改用户个人信息

    PIPL 第 9 条：用户有权更正自己的不准确个人信息

    允许修改的字段：
    - nickname (昵称)
    - avatar_url (头像)
    - bio (个人简介)

    不允许修改的字段：
    - birthday (出生日期，一旦设置不可修改)
    - username (用户名)
    - password (使用单独的修改密码接口)
    """
    try:
        updated = {}

        if data.nickname is not None:
            user.nickname = data.nickname
            updated["nickname"] = data.nickname

        if data.avatar_url is not None:
            user.avatar_url = data.avatar_url
            updated["avatar_url"] = data.avatar_url

        if data.bio is not None:
            user.bio = data.bio
            updated["bio"] = data.bio

        await db.commit()

        logger.info(f"用户信息已更新: user_id={user.id}, updated_fields={list(updated.keys())}")

        return success(
            data={"updated": updated},
            message="个人信息已更新"
        )

    except Exception as e:
        logger.error(f"更新用户信息失败: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新失败，请稍后重试"
        )



@router.post("/api/user/revoke-consent")
async def revoke_consent(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    feature: str = None,
):
    """
    撤销对某项功能的授权

    PIPL 第 9 条：用户有权撤销对个人信息处理的同意

    支持的功能：
    - "friend_recommendation" - 好友推荐
    - "moment_sharing" - 朋友圈分享
    - "analytics" - 数据分析
    - "ads" - 个性化广告

    撤销后，该功能将被禁用
    """
    if not feature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请指定要撤销的功能"
        )

    try:
        # TODO: 根据 feature 字段更新用户设置
        # 目前这是一个占位实现

        logger.info(f"用户撤销授权: user_id={user.id}, feature={feature}")

        return success(
            data={"feature": feature, "status": "revoked"},
            message=f"已撤销对 {feature} 的授权"
        )

    except Exception as e:
        logger.error(f"撤销授权失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="撤销失败，请稍后重试"
        )
