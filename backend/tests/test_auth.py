"""
认证 / BYOK 加密 单元测试 —— 纯函数，无需数据库。

覆盖：API Key at-rest 加密往返、历史明文兼容、Key 脱敏、bcrypt 密码哈希、JWT 签发、lunaris_id 生成。
"""
import uuid

from config.settings import get_settings
from core.crypto import decrypt, encrypt
from services.api_config_service import ApiConfigService
from services.auth_service import AuthService


# ---------------- API Key 加密（BYOK-04） ----------------
def test_crypto_roundtrip():
    key = "sk-test-1234567890abcdef"
    token = encrypt(key)
    assert token.startswith("enc:")
    assert token != key
    assert decrypt(token) == key


def test_crypto_legacy_plaintext_compat():
    # 历史明文（无 enc: 前缀）直接原样返回，迁移零成本
    assert decrypt("legacy-plain-key") == "legacy-plain-key"


def test_crypto_empty():
    assert encrypt("") == ""
    assert decrypt("") == ""


def test_crypto_unique_nonce():
    key = "sk-same-key"
    assert encrypt(key) != encrypt(key)  # 每次随机 nonce，密文不同


# ---------------- Key 脱敏 ----------------
def test_mask_key_normal():
    assert ApiConfigService.mask_key("sk-abcdef1234567890") == "sk-a****7890"


def test_mask_key_short():
    assert ApiConfigService.mask_key("short") == "****rt"


def test_mask_key_none():
    assert ApiConfigService.mask_key(None) is None


def test_mask_key_on_encrypted_value():
    ct = encrypt("sk-abcdef1234567890")
    assert ApiConfigService.mask_key(ct) == "sk-a****7890"


# ---------------- 密码哈希 ----------------
def test_password_hash_roundtrip():
    hashed = AuthService.hash_password("secret123")
    assert hashed != "secret123"
    assert AuthService.verify_password("secret123", hashed)
    assert not AuthService.verify_password("wrong-password", hashed)


# ---------------- JWT / lunaris_id ----------------
def test_create_token_payload():
    uid = uuid.uuid4()
    token = AuthService.create_token(uid)
    assert isinstance(token, str) and token

    from jose import jwt
    payload = jwt.decode(token, get_settings().JWT_SECRET, algorithms=["HS256"])
    assert payload["sub"] == str(uid)


def test_generate_lunaris_id():
    lid = AuthService.generate_lunaris_id()
    assert lid.startswith("luna_")
    assert len(lid) == 13  # "luna_" + 8 位 hex
