import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from common.helpers import opposite_gender
from dao.v1_0.friendship_dao import FriendshipDAO
from dao.v1_0.soul_dao import SoulDAO
from models import Friendship


class MatchingService:
    @staticmethod
    async def auto_match(
            db: AsyncSession,
            user_id: uuid.UUID,
            user_gender: str,
    )->Friendship:
        """
        为用户自动配对一个异性 AI 角色，并创建 friendship 记录

        算法：
        1. 性别匹配：用户为 male → 找 female 角色；用户为 female → 找 male 角色
        2. 优先级：is_default=True 优先
        3. 次优先级：sort_order 升序
        4. 如果没有符合条件的角色，返回 None（后续可兜底）
        """
        # 目标性别: 与用户性别相反
        target_gender = opposite_gender(user_gender)

        # 查询匹配的角色（默认优先 + 排序）
        soul = await SoulDAO.get_match(db, target_gender)
        if not soul:
            raise ValueError(f"没找到合适的{target_gender}角色,请先插入种子数据")

        # 检查是否已有 friendship（防止重复配对）
        existing_friendship = await FriendshipDAO.get_by_user_soul(db, user_id, soul.id)
        if existing_friendship:
            return existing_friendship

        # 创建 friendship（由调用方 commit）
        return await FriendshipDAO.create(
            db,
            user_id=user_id,
            soul_id=soul.id,
            is_primary=True,
            intimacy_level=0,
            nickname=None,
        )

