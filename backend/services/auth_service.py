# backend/services/auth_service.py
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
import bcrypt
from jose import jwt

from config.settings import get_settings
from config.logging_config import get_logger
from dao.user_dao import UserDAO
from models.user import User

logger = get_logger("auth_service")

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AgeVerificationError(Exception):
    """年龄验证错误"""
    pass


class AuthService:
    @staticmethod
    def generate_lunaris_id() -> str:
        """生成唯一主页 ID（微信式微信号）：luna_ + 8 位随机 hex。"""
        return "luna_" + secrets.token_hex(4)

    @staticmethod
    def verify_age(birthday: datetime) -> dict:
        """
        验证年龄并返回年龄信息

        中国《个人信息保护法》第 35 条：
        - 14 岁以下：拒绝注册
        - 14-18 岁：需要监护人确认
        - 18 岁以上：正常注册

        Args:
            birthday: 用户出生日期

        Returns:
            {
                "age": int,
                "can_register": bool,
                "needs_guardian": bool,
                "message": str
            }

        Raises:
            AgeVerificationError: 如果用户年龄不符合要求
        """
        if not birthday:
            # 如果没有提供生日，默认允许（假设为成年人）
            return {
                "age": None,
                "can_register": True,
                "needs_guardian": False,
                "message": "未提供生日信息，默认允许注册"
            }

        # 计算年龄
        today = datetime.now(timezone.utc).date() if isinstance(datetime.now(), datetime) else datetime.now().date()
        if isinstance(birthday, datetime):
            birthday_date = birthday.date()
        else:
            birthday_date = birthday

        age = today.year - birthday_date.year
        # 检查是否已过生日
        if (today.month, today.day) < (birthday_date.month, birthday_date.day):
            age -= 1

        # 中国 PIPL 合规检查
        if age < 14:
            raise AgeVerificationError(
                f"年龄不符合要求：本应用仅限 14 岁及以上用户使用。"
                f"你目前的年龄为 {age} 岁。请稍后再尝试。"
            )

        return {
            "age": age,
            "can_register": True,
            "needs_guardian": age < 18,
            "message": f"年龄验证通过：{age} 岁" +
                      (" (需要监护人确认)" if age < 18 else "")
        }

    @staticmethod
    def hash_password(password: str) -> str:
        # bcrypt 限制最大 72 字节，按字节截断（加密与校验必须一致）
        return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        # 校验时同样按字节截断，保持一致性
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))

    @staticmethod
    def create_token(user_id: uuid.UUID) -> str:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_EXPIRE_DAYS)
        payload = {
            "sub": str(user_id),
            "exp": expire,
            "iat": datetime.now(timezone.utc),
        }
        return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

    @staticmethod
    async def register_user(
        db: AsyncSession,
        username: str,
        password: str,
        gender: str,
        nickname: Optional[str] = None,
        birthday: Optional[datetime] = None,
        guardian_email: Optional[str] = None,
    ) -> User:
        """
        用户注册

        中国 PIPL 合规流程：
        1. 验证年龄
        2. 如果 14-18 岁，发送监护人确认邮件
        3. 创建用户账户

        Args:
            db: 数据库连接
            username: 用户名
            password: 密码
            gender: 性别
            nickname: 昵称
            birthday: 出生日期
            guardian_email: 监护人邮箱（14-18岁需要）

        Raises:
            ValueError: 用户名已存在
            AgeVerificationError: 年龄不符合要求
        """
        # 检查用户名是否已存在
        if await UserDAO.get_by_username(db, username):
            logger.warning("注册失败：用户名已存在", extra={"username": username})
            raise ValueError("用户名已被注册")

        # 验证年龄（PIPL 第 35 条）
        age_info = AuthService.verify_age(birthday)

        # 如果是 14-18 岁，需要监护人邮箱
        if age_info["needs_guardian"] and not guardian_email:
            logger.warning("注册失败：14-18 岁用户缺少监护人邮箱", extra={"username": username})
            raise ValueError(
                f"你的年龄为 {age_info['age']} 岁。"
                f"根据《个人信息保护法》第 35 条，需要提供监护人邮箱。"
            )

        # 创建用户
        user = await UserDAO.create(
            db,
            username=username,
            lunaris_id=AuthService.generate_lunaris_id(),
            password_hash=AuthService.hash_password(password),
            gender=gender,
            nickname=nickname or username,
            birthday=birthday,
        )

        # 如果需要监护人确认，发送邮件
        if age_info["needs_guardian"]:
            from services.guardian_email_service import GuardianEmailService
            await GuardianEmailService.send_guardian_verification_email(
                user_id=user.id,
                username=username,
                guardian_email=guardian_email,
            )
            # 暂时禁用账户，等待监护人确认
            user.is_active = False

        # 注册后自动匹配异性伴侣
        from services.matching_service import MatchingService
        try:
            await MatchingService.auto_match(db, user.id, gender)
        except Exception as e:
            logger.error(f"自动配对失败: {e}", extra={"user_id": str(user.id)}, exc_info=True)

        await db.commit()
        logger.info("用户注册成功", extra={"user_id": str(user.id), "username": username})
        return user

    @staticmethod
    async def login_user(
        db: AsyncSession,
        username: str,
        password: str,
    ) -> Optional[User]:
        user = await UserDAO.get_by_username(db, username)
        if not user:
            logger.info("登录失败：用户不存在", extra={"username": username})
            return None
        if not AuthService.verify_password(password, user.password_hash):
            logger.warning("登录失败：密码错误", extra={"username": username})
            return None
        # 该列是 timestamp without time zone，asyncpg 拒绝带时区值，故存 naive UTC
        user.last_login_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.commit()
        logger.info("用户登录成功", extra={"user_id": str(user.id), "username": username})
        return user

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
        return await UserDAO.get(db, user_id)

    @staticmethod
    async def change_password(
        db: AsyncSession,
        user: User,
        old_password: str,
        new_password: str,
    ) -> bool:
        """修改用户密码"""
        if not AuthService.verify_password(old_password, user.password_hash):
            return False
        user.password_hash = AuthService.hash_password(new_password)
        await db.commit()
        return True
