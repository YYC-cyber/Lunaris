# backend/dao/document_dao.py
"""DocumentDAO —— 知识库文档数据访问。"""
import uuid
from typing import List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from dao.base import BaseDAO
from models.document import Document, DocumentChunk


class DocumentDAO(BaseDAO[Document]):
    model = Document

    @classmethod
    async def list_by_user(cls, db: AsyncSession, user_id: uuid.UUID) -> List[Document]:
        stmt = (
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(Document.created_at.desc())
        )
        return list((await db.execute(stmt)).scalars().all())

    @classmethod
    async def get_by_id_and_user(
        cls, db: AsyncSession, doc_id: int, user_id: uuid.UUID
    ) -> Optional[Document]:
        return (
            await db.execute(
                select(Document).where(Document.id == doc_id, Document.user_id == user_id)
            )
        ).scalar_one_or_none()

    @classmethod
    async def delete_by_user(cls, db: AsyncSession, user_id: uuid.UUID) -> int:
        result = await db.execute(delete(Document).where(Document.user_id == user_id))
        return result.rowcount or 0


class DocumentChunkDAO(BaseDAO[DocumentChunk]):
    model = DocumentChunk

    @classmethod
    async def list_by_document(
        cls, db: AsyncSession, document_id: int
    ) -> List[DocumentChunk]:
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )
        return list((await db.execute(stmt)).scalars().all())

    @classmethod
    async def list_similar(
        cls, db: AsyncSession, document_ids: List[int], query_vec: list, limit: int = 5
    ) -> List[DocumentChunk]:
        """按余弦相似度检索用户文档中最相关的分块。"""
        stmt = (
            select(DocumentChunk)
            .where(
                DocumentChunk.document_id.in_(document_ids),
                DocumentChunk.embedding.is_not(None),
            )
            .order_by(DocumentChunk.embedding.cosine_distance(query_vec))
            .limit(limit)
        )
        return list((await db.execute(stmt)).scalars().all())

    @classmethod
    async def delete_by_document(cls, db: AsyncSession, document_id: int) -> int:
        result = await db.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
        return result.rowcount or 0

    @classmethod
    async def delete_by_user(cls, db: AsyncSession, user_id: uuid.UUID) -> int:
        """删除某用户全部文档分块（账号硬删除用，先据 user_id 关联 documents）。"""
        result = await db.execute(
            delete(DocumentChunk).where(
                DocumentChunk.document_id.in_(
                    select(Document.id).where(Document.user_id == user_id)
                )
            )
        )
        return result.rowcount or 0