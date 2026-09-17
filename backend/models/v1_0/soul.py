# backend/models/soul.py
"""
Soul 模型 —— souls 表（AI 角色）

v1.2：personality 存 SOUL.md 文件路径（完整人设见 backend/data/souls/{name}/SOUL.md，
      由 context_service 的 SoulPromptLoader 加载），改人设只改 md 文件。
"""
from sqlalchemy import Column, Integer, String, Boolean, Text
from sqlalchemy.dialects.postgresql import JSONB

from config.database import Base


class Soul(Base):
    __tablename__ = "souls"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)   # 英文名（小写，对应 SOUL.md 目录名）
    display_name = Column(String(50), nullable=False)                   # 中文显示名
    gender = Column(String(10), nullable=False)                         # 'male' / 'female'
    personality = Column(Text, nullable=False)                          # SOUL.md 文件路径（v1.2）
    first_greeting = Column(Text, nullable=False)                       # 首次配对开场白
    avatar_url = Column(String(255), nullable=True)
    voice_id = Column(String(50), nullable=True)                        # 内部音色 ID（aiden-deep-male 等）
    tts_voice = Column(String(50), nullable=True)                       # Edge TTS 音色（zh-CN-YunjianNeural）
    tts_rate = Column(String(10), nullable=True, default="+0%")         # 基础语速（情绪在此基础上叠加）
    tags = Column(JSONB, nullable=True, default=list)                   # ['温柔','诗人','细腻']
    is_default = Column(Boolean, default=False)                         # 是否默认推荐
    sort_order = Column(Integer, default=0)                             # 排序权重
    daily_motto = Column(Text, nullable=True)                           # 当日心语（可为 JSON 列表循环显示，或固定一句）

