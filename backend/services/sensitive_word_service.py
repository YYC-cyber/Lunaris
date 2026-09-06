"""
敏感词服务 —— 处理敏感词业务逻辑，包括缓存管理
"""

import uuid
import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from dao.sensitive_word_dao import SensitiveWordDAO
from models.sensitive_word import SensitiveWord


class SensitiveWordService:
    """敏感词服务"""

    # 缓存配置
    _cache: Optional[List[str]] = None
    _cache_expire_at: Optional[datetime] = None
    _cache_ttl = 3600  # 1小时 TTL
    _cache_lock = asyncio.Lock()

    @classmethod
    async def load_active_words(cls, db: AsyncSession) -> List[str]:
        """
        加载活跃的敏感词列表（带缓存）

        - 如果缓存未过期则直接返回
        - 否则从数据库加载并缓存
        - 如果数据库操作失败，降级使用文件词库
        """
        now = datetime.utcnow()

        # 检查缓存是否有效
        if (
            cls._cache is not None
            and cls._cache_expire_at is not None
            and now < cls._cache_expire_at
        ):
            return cls._cache

        # 缓存已过期或不存在，从数据库加载
        try:
            async with cls._cache_lock:
                # 双重检查（避免并发重复加载）
                if (
                    cls._cache is not None
                    and cls._cache_expire_at is not None
                    and now < cls._cache_expire_at
                ):
                    return cls._cache

                words = await SensitiveWordDAO.get_all_active_words(db)
                cls._cache = words
                cls._cache_expire_at = now + timedelta(seconds=cls._cache_ttl)
                return words
        except Exception as e:
            print(f"⚠️ 加载数据库敏感词失败: {e}，降级使用文件词库")
            # 降级到文件词库
            return cls._load_file_words()

    @staticmethod
    def _load_file_words() -> List[str]:
        """从文件加载敏感词（降级方案）"""
        from pathlib import Path
        data_dir = Path(__file__).resolve().parent.parent / "data"
        words_file = data_dir / "sensitive_words.txt"

        if not words_file.exists():
            return []

        words = []
        for line in words_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            words.append(line.lower())
        return words

    @classmethod
    def _invalidate_cache(cls):
        """使缓存失效"""
        cls._cache = None
        cls._cache_expire_at = None

    @classmethod
    async def add_word(
        cls,
        db: AsyncSession,
        word: str,
        category: Optional[str] = None,
        created_by: Optional[uuid.UUID] = None,
        effective_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None,
    ) -> SensitiveWord:
        """添加敏感词"""
        sensitive_word = await SensitiveWordDAO.add_word(
            db,
            word=word,
            category=category,
            created_by=created_by,
            effective_at=effective_at,
            expires_at=expires_at,
        )
        cls._invalidate_cache()
        return sensitive_word

    @classmethod
    async def remove_word(cls, db: AsyncSession, word: str) -> bool:
        """删除敏感词"""
        success = await SensitiveWordDAO.remove_word(db, word)
        if success:
            cls._invalidate_cache()
        return success

    @classmethod
    async def update_word(
        cls,
        db: AsyncSession,
        word: str,
        is_active: Optional[bool] = None,
        category: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> Optional[SensitiveWord]:
        """更新敏感词"""
        sensitive_word = await SensitiveWordDAO.update_word(
            db,
            word,
            is_active=is_active,
            category=category,
            expires_at=expires_at,
        )
        if sensitive_word:
            cls._invalidate_cache()
        return sensitive_word

    @classmethod
    async def get_stats(cls, db: AsyncSession) -> Dict:
        """获取敏感词统计"""
        active_count = await SensitiveWordDAO.count_active(db)
        inactive_count = await SensitiveWordDAO.count_inactive(db)
        by_category = await SensitiveWordDAO.count_by_category(db)
        return {
            "active_count": active_count,
            "inactive_count": inactive_count,
            "total_count": active_count + inactive_count,
            "by_category": by_category,
        }
