# backend/tasks/group_message_cleanup_task.py
"""清理过期群聊消息"""

from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from config.settings import get_settings
from models.v1_0.group_chat import GroupMessage
from ws.connection_manager import get_connection_manager
import logging

logger = logging.getLogger("group_message_cleanup")


async def cleanup_expired_messages() -> None:
    """清理所有过期的群聊消息（自动删除）"""
    try:
        settings = get_settings()
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        connection_manager = get_connection_manager()

        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as db_session:
            # 查找所有过期消息（expires_at <= now 且 is_deleted = False）
            stmt = select(GroupMessage).where(
                GroupMessage.expires_at <= datetime.now(),
                GroupMessage.is_deleted == False,
            )
            result = await db_session.execute(stmt)
            expired_messages = result.scalars().all()

            if expired_messages:
                # 获取涉及的群聊 ID
                group_ids = set()
                for msg in expired_messages:
                    group_ids.add(msg.group_id)

                # 标记为已删除
                update_stmt = (
                    update(GroupMessage)
                    .where(
                        GroupMessage.expires_at <= datetime.now(),
                        GroupMessage.is_deleted == False,
                    )
                    .values(is_deleted=True)
                )
                await db_session.execute(update_stmt)
                await db_session.commit()

                deleted_count = len(expired_messages)
                logger.info(f"✅ 群聊消息清理完成: 标记 {deleted_count} 条已过期消息")

                # 推送消息删除事件给群组的所有成员
                from dao.v1_0.group_chat_dao import GroupMemberDAO

                for group_id in group_ids:
                    try:
                        members = await GroupMemberDAO.get_members(db_session, group_id, status="active")
                        for member in members:
                            if member.member_type == "human" and member.member_id:
                                # 推送事件给真人成员
                                await connection_manager.push(
                                    user_id=str(member.member_id),
                                    event_type="group_messages_expired",
                                    event_id=f"group_{group_id}_cleanup",
                                    data={
                                        "group_id": group_id,
                                        "expired_count": sum(1 for m in expired_messages if m.group_id == group_id),
                                    },
                                )
                    except Exception as e:
                        logger.warning(f"⚠️  推送清理事件失败 (group_id={group_id}): {e}")
            else:
                logger.debug("✅ 群聊消息清理完成: 没有过期消息")

        await engine.dispose()
    except Exception as e:
        logger.error(f"❌ 群聊消息清理失败: {e}")
