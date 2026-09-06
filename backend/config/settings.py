# backend/config/settings.py
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# .env 固定位于 backend/.env，按 settings.py 的文件位置解析，不依赖运行时工作目录
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",  # 允许 .env 有多余变量，不报错
    )

    # ---- 数据库（必填） ----
    DATABASE_URL: str = Field(..., description="PostgreSQL 异步连接串")

    # ---- JWT 鉴权（必填） ----
    JWT_SECRET: str = Field(..., description="JWT 签名密钥，生产环境务必更换")
    JWT_EXPIRE_DAYS: int = 30

    # ---- 外部 AI API（可选，留空也能启动） ----
    DEEPSEEK_API_KEY: str = Field("", description="DeepSeek API 密钥")
    DEEPSEEK_BASE_URL: str = Field("https://api.deepseek.com/v1", description="DeepSeek Base URL")
    DEEPSEEK_MODEL: str = Field("deepseek-v4-flash", description="模型名称")

    WHISPER_API_KEY: str = Field("", description="Whisper API 密钥（云转写可选）")
    # ---- 本地 whisper.cpp（免 key，默认）----
    WHISPER_USE_LOCAL: bool = Field(True, description="优先用本地 whisper.cpp 转写")
    WHISPER_MODEL_PATH: str = Field("", description="GGML 模型路径；留空用 backend/data/whisper/models/ggml-base.bin")
    WHISPER_TIMEOUT: int = Field(120, description="本地转写超时秒数")
    TTS_API_KEY: str = Field("", description="TTS API 密钥")
    IMAGE_API_KEY: str = Field("", description="Image API 密钥")
    # ---- 长期记忆语义检索 embedding（可选；留空则用关键词哈希兜底）----
    EMBEDDING_API_KEY: str = Field("", description="长期记忆 embedding API 密钥（OpenAI 兼容）")
    EMBEDDING_BASE_URL: str = Field("https://api.siliconflow.cn/v1", description="Embedding Base URL")
    EMBEDDING_MODEL: str = Field("BAAI/bge-m3", description="Embedding 模型名")


    # ---- 业务配置 ----
    # 注意：.env 里写成逗号分隔字符串即可。
    # pydantic-settings 对 List[str] 字段会先按 JSON 解析，逗号分隔会直接抛
    # SettingsError（且发生在 field_validator 之前），所以这里用 str + 属性转 List。
    RSS_FEED_URLS: str = Field(..., description="RSS 订阅源 URL 列表（逗号分隔）")
    CRISIS_HOTLINES: str = Field(..., description="危机援助热线列表（逗号分隔）")
    CRISIS_WORDS_FILE: str = Field(
        "backend/data/crisis_words.txt", description="危机敏感词表路径（相对仓库根目录）"
    )

    # ---- WebSocket 与实时 ----
    WS_PING_INTERVAL: int = 30

    # ---- CORS 跨域 ----
    CORS_ORIGINS: str = Field(
        "http://localhost:5173,http://localhost:8000,file://",
        description="允许的跨域来源（逗号分隔）",
    )

    # ---- 限流 ----
    RATE_LIMIT_PER_MIN: int = 60

    # ---- 内容安全 ----
    # 语义审核层（DeepSeek 分类涉黄/暴力/诱导）：每次消息多一次 LLM 调用，默认关省成本
    ENABLE_SEMANTIC_SCAN: bool = False

    # ---- 项目路径 ----
    BASE_DIR: Path = Path(__file__).resolve().parent.parent

    # ---- 逗号分隔字符串 → List 辅助 ----
    @property
    def rss_feed_url_list(self) -> List[str]:
        return _split_csv(self.RSS_FEED_URLS)

    @property
    def crisis_hotlines_list(self) -> List[str]:
        return _split_csv(self.CRISIS_HOTLINES)

    @property
    def cors_origins_list(self) -> List[str]:
        return _split_csv(self.CORS_ORIGINS)


def _split_csv(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
