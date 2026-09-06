"""
数据加密服务 - 用于 at-rest 加密敏感数据

用途：
1. 加密危机事件的用户输入文本
2. 加密用户的 API 配置密钥
3. 其他敏感字段的加密

算法: AES-256-GCM (高安全性)
密钥: 从 ENCRYPTION_KEY 环境变量读取
"""

import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import base64
import logging

logger = logging.getLogger(__name__)


class EncryptionService:
    """
    数据加密和解密服务
    使用 AES-256-GCM 算法
    """

    def __init__(self):
        """初始化加密服务，从环境变量读取密钥"""
        encryption_key_hex = os.getenv("ENCRYPTION_KEY")

        if not encryption_key_hex:
            raise ValueError(
                "ENCRYPTION_KEY 环境变量未设置！"
                "请在 .env 中添加: ENCRYPTION_KEY=<64字符十六进制字符串>"
            )

        # 将十六进制字符串转换为字节
        try:
            self.key = bytes.fromhex(encryption_key_hex)
            if len(self.key) != 32:  # AES-256 需要 32 字节
                raise ValueError(
                    f"ENCRYPTION_KEY 长度错误：期望 32 字节（64 字符十六进制），"
                    f"实际 {len(self.key)} 字节"
                )
        except ValueError as e:
            logger.error(f"ENCRYPTION_KEY 格式错误: {e}")
            raise

    def encrypt(self, plaintext: str) -> dict:
        """
        加密纯文本

        Args:
            plaintext: 要加密的字符串

        Returns:
            {
                "iv": "十六进制初始化向量",
                "ciphertext": "十六进制密文"
            }

        示例：
            service = EncryptionService()
            encrypted = service.encrypt("敏感数据")
            # 返回: {"iv": "abc123...", "ciphertext": "def456..."}
        """
        try:
            # 生成随机 IV（初始化向量）- 96 bit (12 字节) 对 GCM 模式最优
            iv = os.urandom(12)

            # 创建 AES-256-GCM 密码对象
            cipher = AESGCM(self.key)

            # 加密数据（plaintext -> ciphertext）
            plaintext_bytes = plaintext.encode("utf-8")
            ciphertext = cipher.encrypt(iv, plaintext_bytes, None)

            # 返回十六进制编码的 IV 和密文
            result = {
                "iv": iv.hex(),
                "ciphertext": ciphertext.hex(),
            }

            logger.debug(f"数据加密成功，长度: {len(plaintext_bytes)} → {len(ciphertext)}")
            return result

        except Exception as e:
            logger.error(f"加密失败: {e}")
            raise

    def decrypt(self, encrypted_data: dict) -> str:
        """
        解密密文

        Args:
            encrypted_data: {
                "iv": "十六进制初始化向量",
                "ciphertext": "十六进制密文"
            }

        Returns:
            解密后的原始字符串

        示例：
            service = EncryptionService()
            plaintext = service.decrypt(encrypted_data)
            # 返回: "敏感数据"
        """
        try:
            # 从十六进制解码
            iv = bytes.fromhex(encrypted_data["iv"])
            ciphertext = bytes.fromhex(encrypted_data["ciphertext"])

            # 验证 IV 长度
            if len(iv) != 12:
                raise ValueError(f"IV 长度错误：期望 12 字节，实际 {len(iv)}")

            # 创建 AES-256-GCM 密码对象
            cipher = AESGCM(self.key)

            # 解密数据
            plaintext_bytes = cipher.decrypt(iv, ciphertext, None)
            plaintext = plaintext_bytes.decode("utf-8")

            logger.debug(f"数据解密成功，长度: {len(ciphertext)} → {len(plaintext_bytes)}")
            return plaintext

        except Exception as e:
            logger.error(f"解密失败: {e}")
            raise

    @staticmethod
    def derive_key_from_password(password: str, salt: bytes = None) -> tuple:
        """
        从密码派生密钥（可选，用于额外的密钥管理）

        Args:
            password: 用户密码
            salt: 盐值（如果 None，生成新的）

        Returns:
            (key, salt) 元组

        【注意】这个方法目前未使用，保留以供未来用途
        """
        if salt is None:
            salt = os.urandom(16)

        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = kdf.derive(password.encode())
        return key, salt


# 全局单例实例
try:
    _encryption_service = EncryptionService()
except Exception as e:
    logger.error(f"无法初始化加密服务: {e}")
    _encryption_service = None


def get_encryption_service() -> EncryptionService:
    """获取全局加密服务实例"""
    if _encryption_service is None:
        raise RuntimeError(
            "加密服务未初始化。请检查 ENCRYPTION_KEY 环境变量。"
        )
    return _encryption_service
