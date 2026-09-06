# backend/models/document.py
"""
Document / DocumentChunk 模型 —— 知识库（RAG）文档与分块

【documents 表】
- id           SERIAL   PRIMARY KEY
- user_id      UUID     FK → users.id
- file_name    VARCHAR  原始文件名
- file_type    VARCHAR  txt / pdf / docx
- file_size    INT      原始字节数
- file_url     VARCHAR  落盘路径
- status       VARCHAR  processing / ready / failed
- chunk_count  INT      分块数
- created_at   TIMESTAMP

【document_chunks 表】
- id           SERIAL   PRIMARY KEY
- document_id  INT      FK → documents.id
- content      TEXT     分块文本
- chunk_index  INT      分块序号
- embedding    VECTOR   语义向量（pgvector, 1536 维）
- metadata     JSONB    预留元数据
- created_at   TIMESTAMP
"""
from sqlalchemy import Column, DateTime, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as UUID_PG, JSONB as PG_JSONB
from pgvector.sqlalchemy import Vector

from config.database import Base
from clients.embedding_client import EMBEDDING_DIM


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID_PG(as_uuid=True), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)     # txt / pdf / docx
    file_size = Column(Integer, nullable=True)
    file_url = Column(String(500), nullable=True)
    status = Column(String(20), nullable=False, default="processing")  # processing / ready / failed
    chunk_count = Column(Integer, nullable=True, default=0)
    created_at = Column(DateTime, server_default=func.now())


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, nullable=False, index=True)
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=True)
    embedding = Column(Vector(EMBEDDING_DIM), nullable=True)
    meta = Column('metadata', PG_JSONB(astext_type=Text()), nullable=True)  # 对应 DB 列 metadata
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_document_chunks_doc_idx", "document_id", "chunk_index"),
    )