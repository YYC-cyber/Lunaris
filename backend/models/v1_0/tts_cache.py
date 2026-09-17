"""TtsCache 模型 —— tts_cache 表（语音合成缓存，参考 lee-agent 的 SQLite 缓存）

【字段】
- id         SERIAL       PRIMARY KEY
- cache_key  VARCHAR(64)  UNIQUE, NOT NULL     # MD5(text + voice_id)
- text       TEXT         NOT NULL
- voice_id   VARCHAR(50)
- voice_url  TEXT         NOT NULL
- hit_count  INT          DEFAULT 0
- created_at TIMESTAMP    DEFAULT NOW()

【索引】
- UNIQUE(cache_key)

【说明】
- CHAT-04 语音回复频繁出现相同文案时命中缓存，免重复调用 TTS
  （性能要求：语音合成 < 3s）
- 由 clients/tts_client.py 维护读写；无独立 DAO，直接内联在 client
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, UniqueConstraint, func

from config.database import Base


class TtsCache(Base):
    __tablename__ = "tts_cache"

    id = Column(Integer, primary_key=True, index=True)
    cache_key = Column(String(64), nullable=False, unique=True)
    text = Column(Text, nullable=False)
    voice_id = Column(String(50), nullable=True)
    voice_url = Column(Text, nullable=False)
    hit_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('cache_key', name='uq_tts_cache_cache_key'),
    )
