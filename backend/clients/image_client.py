"""
图片客户端（Gitee AI）—— 框架占位，按注释实现。

【方法】
- generate(prompt: str, size='1024x1024') -> str(url)
  # 根据提示词生成图片，返回可访问 URL
  # 失败降级：返回预置兜底图 URL（图库）

【说明】MOM-02：朋友圈配图由 AI 生成或从图库兜底
"""

# backend/clients/image_client.py
"""
图片生成客户端 —— 调用外部 API 生成配图

【职责】
- 根据 prompt 生成图片，返回图片 URL
- 支持多服务商（Gitee AI / 占位图兜底）
- 生成失败时返回占位图 URL

【配置】
从 settings 读取 IMAGE_API_KEY
"""

import httpx
from typing import Optional
from urllib.parse import quote

from config.settings import get_settings

settings = get_settings()


class ImageClient:
    def __init__(self):
        self.api_key = settings.IMAGE_API_KEY
        self.timeout = 30.0

    async def generate(
        self,
        prompt: str,
        size: str = "1024x1024",
        style: str = "摄影",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> Optional[str]:
        """
        根据提示词生成图片

        :param prompt: 图片描述
        :param size: 图片尺寸
        :param style: 风格（摄影/插画/油画等）
        :param api_key: 可选，覆盖实例默认 key（BYOK：传用户解析出的配置）
        :param base_url: 可选，覆盖默认服务商地址
        :return: 图片 URL，失败返回 None
        """
        key = api_key or self.api_key
        # 没有配置 API Key → 用免费 Pollinations 文生图（免 key，真生成）
        if not key:
            return self._pollinations_image(prompt)

        try:
            # 这里以 Gitee AI 为例（你之前设计文档里用的是 Gitee AI）
            # 如果是其他服务商，替换 URL 和 payload 格式
            url = base_url or "https://api.gitee.ai/v1/images/generations"
            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            }
            payload = {
                "prompt": f"{style}风格, {prompt}",
                "size": size,
                "n": 1,
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                # 根据实际 API 响应格式提取 URL
                # Gitee AI 返回格式: {"data": [{"url": "..."}]}
                return data.get("data", [{}])[0].get("url")

        except Exception as e:
            print(f"⚠️ 图片生成失败: {e}")
            return self._pollinations_image(prompt)

    def _pollinations_image(self, prompt: str) -> str:
        """免费文生图（Pollinations.ai，免 key）：返回按 prompt 生成的图片 URL。"""
        encoded = quote(prompt)
        return f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true"


# 全局单例
_image_client = None


def get_image_client() -> ImageClient:
    global _image_client
    if _image_client is None:
        _image_client = ImageClient()
    return _image_client