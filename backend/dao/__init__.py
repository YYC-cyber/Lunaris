# dao 包：数据访问层
#
# 【职责】封装所有 SQLAlchemy 查询/写入，业务层（services）通过 DAO 访问数据库。
# 【约定】BaseDAO 提供通用 CRUD；各实体 DAO 继承并补充专用查询方法。
#         事务边界由 service 层控制；DAO 简单场景内部 commit。

from dao.base import BaseDAO
from dao.api_config_dao import ApiConfigDAO
from dao.v1_0.conversation_dao import ConversationDAO
from dao.v1_0.friendship_dao import FriendshipDAO
from dao.v1_0.memory_dao import MemoryDAO
from dao.v1_0.message_dao import MessageDAO
from dao.v1_0.moment_dao import MomentDAO
from dao.v1_0.soul_dao import SoulDAO
from dao.user_dao import UserDAO
from dao.v1_0.user_friendship_dao import UserFriendshipDAO

__all__ = [
    "BaseDAO", "ApiConfigDAO", "ConversationDAO", "FriendshipDAO",
    "MemoryDAO", "MessageDAO", "MomentDAO", "SoulDAO", "UserDAO",
    "UserFriendshipDAO",
]
