# models 包：SQLAlchemy ORM 模型
#
# 【职责】
# - 集中导入所有模型模块，保证 Base.metadata 能被 alembic autogenerate 识别
# - 统一导出模型类，供业务层 `from models import User` 使用
# - 新增模型：写好 models/xxx.py 后，把模块加进下面的导入即可（无需改 alembic/env.py）
#
# 【结构 v1.0】
# - 顶层 models/：通用能力模型（可跨产品复用）：user / user_api_config / audit_log /
#   system_log / permission / sensitive_word / sticker / sticker_favorite /
#   message_edit_history / user_block / appeal / report
# - models/v1_0/：Lunaris 产品业务模型：soul / friendship / message / memory / moment /
#   comment / like / crisis_event / tts_cache / user_friendship / conversation / document /
#   group_chat / group_mute / group_permission / group_announcement / message_favorite
#
# 【约定】每个模型文件只放一个模型类；字段/关系定义见各文件注释

# ---- 通用能力模型模块（顶层）----
from . import (
    user,
    audit_log,
    user_api_config,
    sticker,
    sticker_favorite,
    user_block,
    message_edit_history,
    report,
    appeal,
    sensitive_word,
)

# ---- Lunaris v1.0 业务模型模块（.v1_0 子包；导入以触发 Base.metadata 注册）----
from . import v1_0  # noqa: F401
from .v1_0 import (
    soul,
    friendship,
    message,
    message_favorite,
    moment,
    comment,
    memory,
    crisis_event,
    tts_cache,
    user_friendship,
    conversation,
    group_chat,
    group_mute,
    group_permission,
    group_announcement,
    document,
    like,
)

# ---- 统一导出模型类 ----
from .user import User
from .user_api_config import UserApiConfig
from .sticker import Sticker
from .sticker_favorite import StickerFavorite
from .user_block import UserBlock
from .message_edit_history import MessageEditHistory
from .audit_log import AuditLog
from .appeal import Appeal
from .report import Report
from .sensitive_word import SensitiveWord

from .v1_0.document import Document, DocumentChunk
from .v1_0.memory import MemoryRecord
from .v1_0.soul import Soul
from .v1_0.friendship import Friendship
from .v1_0.message import Message
from .v1_0.message_favorite import MessageFavorite
from .v1_0.moment import Moment
from .v1_0.comment import Comment
from .v1_0.like import Like
from .v1_0.user_friendship import UserFriendship
from .v1_0.conversation import Conversation
from .v1_0.crisis_event import CrisisEvent
from .v1_0.group_chat import GroupChat, GroupMember, GroupMessage, GroupInvitation, GroupMemory
from .v1_0.group_mute import GroupMute
from .v1_0.group_permission import GroupPermission
from .v1_0.group_announcement import GroupAnnouncement

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
    "soul",
    "friendship",
    "message",
    "message_favorite",
    "moment",
    "comment",
    "memory",
    "crisis_event",
    "tts_cache",
    "user_friendship",
    "conversation",
    "group_chat",
    "group_mute",
    "group_permission",
    "group_announcement",
    "document",
]