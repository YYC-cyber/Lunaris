# models 包：SQLAlchemy ORM 模型
#
# 【职责】
# - 集中导入所有模型模块，保证 Base.metadata 能被 alembic autogenerate 识别
# - 统一导出模型类，供业务层 `from models import User` 使用
# - 新增模型：写好 models/xxx.py 后，把模块加进下面的导入即可（无需改 alembic/env.py）
#
# 【模型清单】
#   User / Soul / Friendship / Message / Moment / Comment
#   Question / Answer / Vote / MemoryRecord
#   CrisisEvent / TtsCache / AuditLog
#
# 【约定】每个模型文件只放一个模型类；字段/关系定义见各文件注释
#
# 注意：目前仅 user.py 已实现 ORM 类，其余文件为字段设计文档（占位）。
#       补充实现后（如 class Soul(Base)），这里会自动发现并参与迁移生成。

# 导入所有模型模块（当前仅 user 有类，其余为文档占位，导入无害）
from . import (
    user,
    soul,
    friendship,
    message,
    message_edit_history,
    message_favorite,
    moment,
    comment,
    memory,
    crisis_event,
    tts_cache,
    audit_log,
    user_friendship,
    user_api_config,
    conversation,
    sticker,
    user_block,
    group_chat,
    group_mute,
    group_permission,
    group_announcement,
    report,
    appeal,
    sensitive_word,
    document,
)

from .user import User

__all__ = [
    "User",
    "MemoryRecord",
    "UserFriendship",
    "UserApiConfig",
    "StickerFavorite",
    "MessageEditHistory",
    "MessageFavorite",
    "GroupChat",
    "GroupMember",
    "GroupMessage",
    "GroupInvitation",
    "GroupMemory",
    "GroupMute",
    "GroupPermission",
    "GroupAnnouncement",
    "Report",
    "Appeal",
    "SensitiveWord",
    "user",
    "soul",
    "friendship",
    "message",
    "message_edit_history",
    "message_favorite",
    "moment",
    "comment",
    "memory",
    "crisis_event",
    "tts_cache",
    "audit_log",
    "user_friendship",
    "user_api_config",
    "conversation",
    "sticker",
    "user_block",
    "group_chat",
    "group_mute",
    "group_permission",
    "group_announcement",
    "report",
    "appeal",
    "sensitive_word",
    "document",
]
from .document import Document, DocumentChunk
from .memory import MemoryRecord
from .soul import Soul
from .friendship import Friendship
from .message import Message
from .message_edit_history import MessageEditHistory
from .message_favorite import MessageFavorite
from .moment import Moment
from .comment import Comment
from .like import Like
from .user_friendship import UserFriendship
from .user_api_config import UserApiConfig
from .conversation import Conversation
from .sticker import Sticker
from .crisis_event import CrisisEvent
from .audit_log import AuditLog
from .sticker_favorite import StickerFavorite
from .user_block import UserBlock
from .group_chat import GroupChat, GroupMember, GroupMessage, GroupInvitation, GroupMemory
from .group_mute import GroupMute
from .group_permission import GroupPermission
from .group_announcement import GroupAnnouncement
from .report import Report
from .appeal import Appeal
from .sensitive_word import SensitiveWord
