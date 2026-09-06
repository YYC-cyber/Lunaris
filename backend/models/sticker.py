# backend/models/sticker.py
"""Sticker 模型 —— stickers 表（表情包，STK）。

【字段】
- id         SERIAL    PRIMARY KEY
- name       VARCHAR   表情名（如「大笑」「哭」）
- emotion    VARCHAR   关联情绪：happy / sad / angry / neutral / love（AI 回表情用）
- image_url  VARCHAR   表情图 URL
- category   VARCHAR   分类（可选）
- sort_order INT       排序
"""
from sqlalchemy import Column, Integer, String

from config.database import Base


class Sticker(Base):
    __tablename__ = "stickers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    emotion = Column(String(20), nullable=False, index=True)  # happy/sad/angry/neutral/love
    image_url = Column(String(255), nullable=False)
    category = Column(String(20), nullable=True)
    sort_order = Column(Integer, default=0)
