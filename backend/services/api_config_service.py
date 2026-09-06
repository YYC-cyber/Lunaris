# backend/services/api_config_service.py
"""API 配置服务（BYOK）—— 用户自带的第三方 API Key。

【服务类型】
llm / vision / whisper / tts / image

【职责】
- upsert：保存/更新某服务的配置
- get_all_configs：读取某用户全部配置（接口返回脱敏 Key）
- resolve：客户端调用时解析某服务的配置（优先用户配置，回退全局 settings）
"""
import uuid
from typing import Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from dao.api_config_dao import ApiConfigDAO
from dao.user_dao import UserDAO
from models.user_api_config import UserApiConfig

SERVICES = ("llm", "vision", "whisper", "tts", "image")


class ApiConfigService:
    @staticmethod
    async def get_config(
        db: AsyncSession, user_id: uuid.UUID, service: str
    ) -> Optional[UserApiConfig]:
        if service not in SERVICES:
            raise ValueError(f"未知服务: {service}")
        return await ApiConfigDAO.get_by_user_service(db, user_id, service)

    @staticmethod
    async def get_all_configs(
        db: AsyncSession, user_id: uuid.UUID
    ) -> Dict[str, UserApiConfig]:
        configs = await ApiConfigDAO.list_by_user(db, user_id)
        return {c.service: c for c in configs}

    @staticmethod
    async def upsert_config(
        db: AsyncSession,
        user_id: uuid.UUID,
        service: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ) -> UserApiConfig:
        """保存/更新某服务配置。api_key 为空则保持原值（用于只改 model）。

        api_key 落库前加密（BYOK-04 at-rest 加密）；历史明文兼容。
        """
        from core.crypto import encrypt
        config = await ApiConfigService.get_config(db, user_id, service)
        if config:
            return await ApiConfigDAO.update(
                db, config,
                api_key=encrypt(api_key) if api_key else config.api_key,
                base_url=base_url if base_url is not None else config.base_url,
                model=model if model is not None else config.model,
                is_active=True,
            )
        return await ApiConfigDAO.create(
            db,
            user_id=user_id,
            service=service,
            api_key=encrypt(api_key) if api_key else None,
            base_url=base_url or None,
            model=model or None,
        )

    @staticmethod
    def mask_key(api_key: Optional[str]) -> Optional[str]:
        """脱敏：sk-****1234，不回显明文。先解密（兼容历史明文）。"""
        from core.crypto import decrypt
        plain = decrypt(api_key) if api_key else None
        if not plain:
            return None
        if len(plain) <= 8:
            return "****" + plain[-2:]
        return plain[:4] + "****" + plain[-4:]

    # service → (settings 的 API_KEY 属性, BASE_URL 属性, MODEL 属性)
    _FALLBACK_ATTRS = {
        "llm": ("DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL"),
        "vision": ("DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL"),  # 视觉暂复用 LLM
        "whisper": ("WHISPER_API_KEY", None, None),
        "tts": ("TTS_API_KEY", None, None),
        "image": ("IMAGE_API_KEY", None, None),
    }

    @staticmethod
    async def resolve(
        db: AsyncSession, user_id: uuid.UUID, service: str
    ) -> dict:
        """解析某服务的有效配置，优先级：
        1. 用户自带配置（BYOK）
        2. 自动配置开关开启 或 用户被后台授权使用平台 API → 用平台 Key
        3. 都没有 → 返回空（功能禁用，提示配置）

        返回 {"api_key", "base_url", "model", "from_user", "provisioned"}
        """
        # 1. 用户自带配置（api_key 解密后返回，供客户端直接使用）
        from core.crypto import decrypt
        config = await ApiConfigService.get_config(db, user_id, service)
        if config and config.api_key:
            return {
                "api_key": decrypt(config.api_key),
                "base_url": config.base_url,
                "model": config.model,
                "from_user": True,
                "provisioned": False,
            }

        # 2. 用户被后台授权使用平台 API → 用平台（env）Key
        granted = await ApiConfigService._is_api_granted(db, user_id)
        if granted:
            from config.settings import get_settings
            s = get_settings()
            key_attr, url_attr, model_attr = ApiConfigService._FALLBACK_ATTRS.get(
                service, (None, None, None)
            )
            return {
                "api_key": getattr(s, key_attr, "") if key_attr else "",
                "base_url": getattr(s, url_attr, None) if url_attr else None,
                "model": getattr(s, model_attr, None) if model_attr else None,
                "from_user": False,
                "provisioned": True,
            }

        # 3. 无 Key → 功能禁用（前端提示去设置/等授权）
        return {
            "api_key": "", "base_url": None, "model": None,
            "from_user": False, "provisioned": False,
        }

    @staticmethod
    async def test_connection(service: str, cfg: dict) -> dict:
        """测试某服务的连接是否可用（BYOK-05）。

        :param service: llm / vision / whisper / tts / image
        :param cfg: 含 api_key / base_url / model 的配置（已解密）
        :return: 成功返回 {model, reply, note}；失败抛异常（由 controller 转成友好提示）
        """
        import httpx
        from clients.llm_client import friendly_llm_error
        api_key = cfg.get("api_key") or ""
        base_url = (cfg.get("base_url") or "").rstrip("/")
        model = cfg.get("model") or ""

        if service == "llm":
            url = f"{base_url or 'https://api.deepseek.com/v1'}/chat/completions"
            payload = {
                "model": model or "deepseek-v4-flash",
                "messages": [{"role": "user", "content": "你好，请回复：ok"}],
                "max_tokens": 16,
                "temperature": 0,
            }
            try:
                async with httpx.AsyncClient(timeout=20, trust_env=False) as client:
                    r = await client.post(
                        url, headers={"Authorization": f"Bearer {api_key}"}, json=payload
                    )
                    r.raise_for_status()
                    content = r.json()["choices"][0]["message"]["content"]
                return {"model": model, "reply": content[:30], "note": "LLM 连接正常"}
            except Exception as e:
                raise ValueError(friendly_llm_error(e, model=model))

        # whisper / tts / image / vision：多为本地或需真实媒体才能测，暂返回已配置
        return {"model": model, "note": "配置已保存（该服务暂不支持在线测试）"}

    @staticmethod
    async def _is_api_granted(db: AsyncSession, user_id: uuid.UUID) -> bool:
        """该用户是否在有效期内被授权使用平台 API（到期自动失效）。"""
        from datetime import datetime, timezone
        user = await UserDAO.get(db, user_id)
        if not user or not user.api_granted_until:
            return False
        now = datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC，与列一致
        return user.api_granted_until > now
