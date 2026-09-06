"""
密钥加密存储（BYOK-04）—— 用户 API Key 落库前加密、读取时解密，接口永不回显明文。

【方案】
- HMAC-SHA256 流式加密（CTR 思想：nonce + 计数器生成密钥流），密钥由 JWT_SECRET 派生。
- 纯标准库实现（hashlib / hmac / os / base64），无需引入 cryptography 额外依赖。
- 密文加 "enc:" 前缀区分；历史明文（无前缀）直接兼容读取，迁移零成本。

【说明】
- 如需更强加密，可替换为 cryptography 的 Fernet / AES-GCM；当前方案满足
  「at-rest 非明文 + 接口脱敏」的产品要求。
- 密钥派生自 JWT_SECRET：更换 JWT_SECRET 后旧密文无法解密（返回空，视为未配置），
  属预期行为，文档中已标注。
"""
import base64
import hashlib
import hmac
import os

_PREFIX = "enc:"


def _derive_key() -> bytes:
    from config.settings import get_settings
    secret = get_settings().JWT_SECRET
    return hashlib.sha256(("lunaris:api-key:v1:" + secret).encode("utf-8")).digest()


def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    """按 CTR 方式用 HMAC 生成 length 字节密钥流。"""
    out = b""
    counter = 0
    while len(out) < length:
        out += hmac.new(key, nonce + counter.to_bytes(4, "big"), hashlib.sha256).digest()
        counter += 1
    return out[:length]


def encrypt(plaintext: str) -> str:
    """加密明文字符串，返回 "enc:<base64(nonce+ct)>"。空串原样返回。"""
    if not plaintext:
        return ""
    key = _derive_key()
    nonce = os.urandom(16)
    data = plaintext.encode("utf-8")
    ct = bytes(a ^ b for a, b in zip(data, _keystream(key, nonce, len(data))))
    return _PREFIX + base64.urlsafe_b64encode(nonce + ct).decode("ascii")


def decrypt(token: str) -> str:
    """解密。"enc:" 前缀 → 解密；无前缀（旧明文）→ 原样返回；失败 → 空串。"""
    if not token:
        return ""
    if not token.startswith(_PREFIX):
        return token  # 历史明文，兼容
    try:
        raw = base64.urlsafe_b64decode(token[len(_PREFIX):].encode("ascii"))
        nonce, ct = raw[:16], raw[16:]
        key = _derive_key()
        pt = bytes(a ^ b for a, b in zip(ct, _keystream(key, nonce, len(ct))))
        return pt.decode("utf-8")
    except Exception:
        return ""
