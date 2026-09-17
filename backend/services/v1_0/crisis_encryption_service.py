"""
危机事件加密服务

中国《个人信息保护法》第 9 条：
- 敏感个人信息必须加密存储
- 自伤/自杀相关内容属于敏感信息
- 仅授权给注册的心理咨询师和管理员访问
"""

import logging
from services.encryption_service import get_encryption_service
from models.v1_0.crisis_event import CrisisEvent

logger = logging.getLogger(__name__)


class CrisisEncryptionService:
    """危机事件加密服务"""

    @staticmethod
    def encrypt_crisis_content(trigger_content: str) -> dict:
        """
        加密危机事件的触发内容

        Args:
            trigger_content: 原始用户输入内容

        Returns:
            {
                "iv": "十六进制初始化向量",
                "ciphertext": "十六进制密文"
            }
        """
        try:
            encryption_service = get_encryption_service()
            encrypted = encryption_service.encrypt(trigger_content)
            logger.debug(f"危机内容已加密（长度：{len(trigger_content)} → {len(encrypted['ciphertext'])}）")
            return encrypted
        except Exception as e:
            logger.error(f"危机内容加密失败: {e}")
            raise

    @staticmethod
    def decrypt_crisis_content(encrypted_data: dict) -> str:
        """
        解密危机事件的触发内容

        Args:
            encrypted_data: {
                "iv": "十六进制初始化向量",
                "ciphertext": "十六进制密文"
            }

        Returns:
            解密后的原始内容
        """
        try:
            encryption_service = get_encryption_service()
            plaintext = encryption_service.decrypt(encrypted_data)
            logger.debug(f"危机内容已解密")
            return plaintext
        except Exception as e:
            logger.error(f"危机内容解密失败: {e}")
            raise

    @staticmethod
    def should_encrypt_crisis_event(crisis_event: CrisisEvent) -> bool:
        """
        判断是否需要加密危机事件

        高风险事件必须加密：
        - risk_level == "critical" 或 "high"
        """
        return crisis_event.risk_level in ["critical", "high"]

    @staticmethod
    def safe_get_trigger_content(crisis_event: CrisisEvent, user_id=None, is_admin=False):
        """
        安全获取危机事件的触发内容

        访问控制：
        - 仅授权给记录者、管理员、心理咨询师
        - 其他用户无法访问

        Args:
            crisis_event: 危机事件对象
            user_id: 请求者的用户 ID
            is_admin: 是否是管理员

        Returns:
            触发内容（如果有访问权限）或 None
        """
        # 访问权限检查
        has_permission = (
            is_admin or
            (user_id and str(user_id) == str(crisis_event.user_id))
            # TODO: 检查是否是注册的心理咨询师
        )

        if not has_permission:
            logger.warning(
                f"未授权访问危机事件: user_id={user_id}, crisis_id={crisis_event.id}"
            )
            return None

        # 如果内容被加密，先解密
        if crisis_event.trigger_content_encrypted:
            try:
                return CrisisEncryptionService.decrypt_crisis_content(
                    crisis_event.trigger_content_encrypted
                )
            except Exception as e:
                logger.error(f"无法解密危机内容: {e}")
                return None

        # 否则返回明文（向后兼容）
        return crisis_event.trigger_content
