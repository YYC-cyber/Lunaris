"""
embedding 客户端 —— 文本向量化（长期记忆语义检索）。

【方案】
1. 配置了 EMBEDDING_API_KEY → 调 OpenAI 兼容 `/embeddings` 接口（语义记忆检索）
2. 未配置 → 关键词哈希兜底（确定性字符 n-gram 哈希到 1536 维，中文可用）
   语义质量不如真 embedding，但能跑通、无需额外 key。

【维度】统一 1536（与长期记忆向量字段一致），
API 返回维度不一致时自动 pad/truncate。
"""
import hashlib
import re

import httpx

from config.settings import get_settings

settings = get_settings()

EMBEDDING_DIM = 1536


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def hash_embed(text: str) -> list:
    """确定性关键词哈希兜底：字符 n-gram 哈希到 1536 维，L2 归一化。

    纯标准库、确定性（同文本同向量），无需任何 API。中文按单字 + 双字 bigram 计算，
    共享字符越多的文本余弦相似度越高，可支撑「关键词级」检索。
    """
    vec = [0.0] * EMBEDDING_DIM
    text = _normalize(text)
    if not text:
        return vec
    for i in range(len(text)):
        tokens = [text[i]]
        if i + 1 < len(text):
            tokens.append(text[i:i + 2])
        for tok in tokens:
            h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
            vec[h % EMBEDDING_DIM] += 1.0
    norm = sum(v * v for v in vec) ** 0.5
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def _pad_truncate(vec: list, dim: int = EMBEDDING_DIM) -> list:
    """把任意维度向量对齐到 dim 维（截断或补零）。"""
    if len(vec) >= dim:
        return list(vec[:dim])
    return list(vec) + [0.0] * (dim - len(vec))


class EmbeddingClient:
    def __init__(self):
        self.api_key = settings.EMBEDDING_API_KEY
        self.base_url = settings.EMBEDDING_BASE_URL
        self.model = settings.EMBEDDING_MODEL
        self.timeout = 30.0

    async def embed(self, text: str) -> list:
        """文本 → 1536 维向量。无 key 或 API 失败时回退哈希。"""
        if not _normalize(text):
            return [0.0] * EMBEDDING_DIM
        if self.api_key:
            try:
                return await self._embed_api(text)
            except Exception as e:
                print(f"⚠️ embedding API 失败，回退哈希: {e}")
        return hash_embed(text)

    async def _embed_api(self, text: str) -> list:
        url = f"{self.base_url.rstrip('/')}/embeddings"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "input": text},
            )
            resp.raise_for_status()
            data = resp.json()
            vec = data["data"][0]["embedding"]
        return _pad_truncate(vec)


# 全局单例
_embedding_client = None


def get_embedding_client() -> EmbeddingClient:
    global _embedding_client
    if _embedding_client is None:
        _embedding_client = EmbeddingClient()
    return _embedding_client
