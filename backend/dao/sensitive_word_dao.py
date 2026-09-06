"""SensitiveWordDAO —— 敏感词数据访问"""
import uuid
from typing import List, Optional, Dict
from datetime import datetime

from sqlalchemy import select, update, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from dao.base import BaseDAO
from models.sensitive_word import SensitiveWord


class SensitiveWordDAO(BaseDAO[SensitiveWord]):
    model = SensitiveWord

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
        return await cls.create(
            db,
            word=word,
            category=category,
            created_by=created_by,
            effective_at=effective_at,
            expires_at=expires_at,
            is_active=True,
        )

    @classmethod
    async def remove_word(
        cls,
        db: AsyncSession,
        word: str,
    ) -> bool:
        """软删除敏感词（设置 is_active=false）"""
        stmt = select(SensitiveWord).where(SensitiveWord.word == word)
        result = await db.execute(stmt)
        sensitive_word = result.scalar_one_or_none()
        if not sensitive_word:
            return False

        sensitive_word.is_active = False
        sensitive_word.updated_at = datetime.utcnow()
        await db.commit()
        return True

    @classmethod
    async def list_active(
        cls,
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0,
        category: Optional[str] = None,
    ) -> List[SensitiveWord]:
        """获取活跃的敏感词（考虑有效期）"""
        now = datetime.utcnow()
        stmt = select(SensitiveWord).where(
            SensitiveWord.is_active == True,
            (SensitiveWord.effective_at.is_(None) | (SensitiveWord.effective_at <= now)),
            (SensitiveWord.expires_at.is_(None) | (SensitiveWord.expires_at > now)),
        )
        if category:
            stmt = stmt.where(SensitiveWord.category == category)

        stmt = stmt.order_by(desc(SensitiveWord.created_at)).limit(limit).offset(offset)
        return list((await db.execute(stmt)).scalars().all())

    @classmethod
    async def get_all_active_words(cls, db: AsyncSession) -> List[str]:
        """获取所有活跃的敏感词（仅词本身）"""
        now = datetime.utcnow()
        stmt = select(SensitiveWord.word).where(
            SensitiveWord.is_active == True,
            (SensitiveWord.effective_at.is_(None) | (SensitiveWord.effective_at <= now)),
            (SensitiveWord.expires_at.is_(None) | (SensitiveWord.expires_at > now)),
        )
        result = await db.execute(stmt)
        return [row[0] for row in result.all()]

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
        stmt = select(SensitiveWord).where(SensitiveWord.word == word)
        result = await db.execute(stmt)
        sensitive_word = result.scalar_one_or_none()
        if not sensitive_word:
            return None

        if is_active is not None:
            sensitive_word.is_active = is_active
        if category is not None:
            sensitive_word.category = category
        if expires_at is not None:
            sensitive_word.expires_at = expires_at

        sensitive_word.updated_at = datetime.utcnow()
        await db.commit()
        return sensitive_word

    @classmethod
    async def count_by_category(cls, db: AsyncSession) -> Dict[str, int]:
        """按分类统计敏感词"""
        stmt = select(
            SensitiveWord.category,
            func.count().label("count")
        ).where(
            SensitiveWord.is_active == True
        ).group_by(
            SensitiveWord.category
        )
        result = await db.execute(stmt)
        return {row[0] or "unknown": row[1] for row in result.all()}

    @classmethod
    async def count_active(cls, db: AsyncSession) -> int:
        """计数活跃的敏感词"""
        now = datetime.utcnow()
        stmt = select(func.count()).select_from(SensitiveWord).where(
            SensitiveWord.is_active == True,
            (SensitiveWord.effective_at.is_(None) | (SensitiveWord.effective_at <= now)),
            (SensitiveWord.expires_at.is_(None) | (SensitiveWord.expires_at > now)),
        )
        return (await db.execute(stmt)).scalar_one()

    @classmethod
    async def count_inactive(cls, db: AsyncSession) -> int:
        """计数禁用的敏感词"""
        stmt = select(func.count()).select_from(SensitiveWord).where(
            SensitiveWord.is_active == False
        )
        return (await db.execute(stmt)).scalar_one()
