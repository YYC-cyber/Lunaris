"""
监护人邮件验证模块 - 测试环境专用
【重要】这个模块仅用于测试，生产环境应替换为真实邮件服务

生产时删除整个模块，替换为真实 SMTP 或第三方邮件服务
"""

import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional

# 🟡 测试用：邮件验证存储（应替换为数据库）
_guardian_verification_store: Dict[str, dict] = {}


class GuardianEmailService:
    """
    监护人邮件验证服务（测试版本）

    生产版本应：
    1. 使用真实 SMTP 发送邮件
    2. 将验证记录存储在数据库
    3. 实现重试机制和邮件模板
    """

    @staticmethod
    def is_email_enabled() -> bool:
        """检查邮件功能是否启用"""
        return os.getenv("ENABLE_GUARDIAN_EMAIL", "false").lower() == "true"

    @staticmethod
    def generate_verification_token(user_id: int, guardian_email: str) -> str:
        """生成监护人验证令牌"""
        token = str(uuid.uuid4())

        # 测试存储（后期删除）
        _guardian_verification_store[token] = {
            "user_id": user_id,
            "guardian_email": guardian_email,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(days=7),
            "verified": False,
        }

        return token

    @staticmethod
    async def send_guardian_verification_email(
        user_id: int,
        username: str,
        guardian_email: str
    ) -> bool:
        """
        发送监护人确认邮件

        测试版本：打印到日志
        生产版本：使用 SMTP 发送真实邮件
        """
        token = GuardianEmailService.generate_verification_token(user_id, guardian_email)

        # 🟡 测试用：打印到控制台和日志
        verification_link = f"http://localhost:8000/api/auth/verify-guardian?token={token}"

        print("\n" + "="*70)
        print("📧 [测试] 监护人确认邮件")
        print("="*70)
        print(f"收件人: {guardian_email}")
        print(f"用户名: {username} (ID: {user_id})")
        print(f"验证令牌: {token}")
        print(f"验证链接: {verification_link}")
        print(f"有效期: 7 天")
        print("\n💡 生产环境：此处应发送真实邮件给监护人")
        print("="*70 + "\n")

        # 记录日志
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            f"Guardian verification email (TEST MODE): "
            f"user_id={user_id}, guardian_email={guardian_email}, token={token}"
        )

        return True

    @staticmethod
    def verify_guardian_token(token: str) -> Optional[Dict]:
        """验证监护人令牌"""
        if token not in _guardian_verification_store:
            return None

        record = _guardian_verification_store[token]

        # 检查过期
        if datetime.now() > record["expires_at"]:
            del _guardian_verification_store[token]
            return None

        # 标记为已验证
        record["verified"] = True
        return record


# 🟡 【生产替换】以下是真实邮件服务的框架（目前未使用）
class RealGuardianEmailService:
    """
    真实邮件服务 - 生产版本使用

    需要的依赖：
    - pip install python-dotenv aiosmtplib email-validator
    """

    @staticmethod
    async def send_guardian_verification_email(
        user_id: int,
        username: str,
        guardian_email: str
    ) -> bool:
        """发送真实邮件给监护人"""
        # TODO: 实现真实邮件发送
        # 1. 从环境变量读取 SMTP 配置
        # 2. 使用 aiosmtplib 异步发送
        # 3. 包含验证链接和有效期
        # 4. 记录发送状态到数据库
        raise NotImplementedError("Use GuardianEmailService for testing, implement this in production")
