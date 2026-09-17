# backend/services/knowledge_service.py
"""知识库（RAG）服务 —— 文档上传、分块、向量化、语义检索、RAG 问答。

【流程】
1. upload：读文件 → 抽取文本 → 按大小分块 → 逐块向量化(embedding) → 入库
2. search：query 向量化 → 检索用户文档下最相似分块（pgvector 余弦距离）
3. rag_answer：search + 组装上下文 → 调 LLM 生成有依据回答
4. delete / list：文档管理与状态查询
"""
import os
import re
import uuid
from pathlib import Path
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from clients.embedding_client import get_embedding_client
from clients.llm_client import LLMClient
from dao.v1_0.document_dao import DocumentChunkDAO, DocumentDAO
from models.v1_0.document import Document, DocumentChunk

# 文档落盘目录（与上传控制器同源，便于静态文件服务）
UPLOAD_DIR = "/tmp/lunaris_uploads"

# 分块策略参数
CHUNK_SIZE = 500          # 每块约 500 字
CHUNK_OVERLAP = 80        # 相邻块重叠，避免打断语义
MAX_FILE_SIZE = 5 * 1024 * 1024  # 单文档 5MB

ALLOWED_TYPES = {"txt", "md"}


def _detect_file_type(filename: str) -> str:
    ext = Path(filename).suffix.lower().lstrip(".") or "txt"
    return ext if ext in ALLOWED_TYPES or ext in {"pdf", "docx"} else "txt"


def _parse_content(content: bytes, file_type: str) -> str:
    """把原始文件字节转为纯文本。"""
    if file_type == "pdf":
        return _parse_pdf(content)
    if file_type == "docx":
        return _parse_docx(content)
    # txt / md / 其他：按 utf-8 解码，失败回退 latin-1，避免乱码崩溃
    for enc in ("utf-8", "utf-8-sig", "gbk", "latin-1"):
        try:
            return content.decode(enc)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="ignore")


def _parse_pdf(content: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ValueError("解析 PDF 需要安装 pypdf：pip install pypdf")
    import io
    reader = PdfReader(io.BytesIO(content))
    pages = [p.extract_text() or "" for p in reader.pages]
    return "\n".join(pages)


def _parse_docx(content: bytes) -> str:
    try:
        from docx import Document as DocxDocument
    except ImportError:
        raise ValueError("解析 Word 需要安装 python-docx：pip install python-docx")
    import io
    doc = DocxDocument(io.BytesIO(content))
    return "\n".join(p.text for p in doc.paragraphs if p.text)


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """按段落优先、其次定长分段策略切分文本。"""
    text = re.sub(r"\r\n", "\n", text or "").strip()
    if not text:
        return []
    # 优先按段落切分
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    chunks: List[str] = []
    cur = ""
    for para in paragraphs:
        # 单个段落超长则按定长硬切
        while len(para) > chunk_size:
            if cur:
                chunks.append(cur)
            cur = para[:chunk_size]
            para = para[chunk_size - overlap:]
        if len(cur) + len(para) > chunk_size:
            chunks.append(cur)
            cur = para
        else:
            cur = (cur + "\n" + para).strip() if cur else para
    if cur:
        chunks.append(cur)
    return chunks


class KnowledgeService:
    def __init__(self):
        self.embedder = get_embedding_client()

    # ---- 文档上传 ----
    async def upload(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        filename: str,
        content: bytes,
    ) -> Document:
        file_type = _detect_file_type(filename)
        if file_type not in ALLOWED_TYPES and file_type not in {"pdf", "docx"}:
            raise ValueError(f"不支持的文件类型：{filename}")

        doc = await DocumentDAO.create(
            db,
            user_id=user_id,
            file_name=filename,
            file_type=file_type,
            file_size=len(content),
            status="processing",
            chunk_count=0,
        )
        # 若 service 内部失败，DAO.create 已 commit，需回滚归档为 failed
        try:
            text = _parse_content(content, file_type)
            chunks = _chunk_text(text)
            if not chunks:
                raise ValueError("未能从文件中提取到有效文本内容")

            # 落盘原始文件，供前端溯源下载
            saved_path = self._save_raw(content, filename)
            doc.file_url = saved_path

            n = 0
            for idx, chunk_text in enumerate(chunks):
                vec = await self.embedder.embed(chunk_text)
                await DocumentChunkDAO.create(
                    db, document_id=doc.id, content=chunk_text,
                    chunk_index=idx, embedding=vec,
                )
                n += 1

            doc.status = "ready"
            doc.chunk_count = n
            await db.commit()
            await db.refresh(doc)
            return doc
        except Exception as e:
            doc.status = "failed"
            doc.chunk_count = 0
            await db.commit()
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"文档处理失败：{e}")

    def _save_raw(self, content: bytes, filename: str) -> str:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        name = f"{uuid.uuid4().hex}_{Path(filename).name}"
        path = os.path.join(UPLOAD_DIR, name)
        with open(path, "wb") as f:
            f.write(content)
        return f"/static/uploads/{name}"

    # ---- 文档列表 ----
    async def list_documents(self, db: AsyncSession, user_id: uuid.UUID) -> List[dict]:
        docs = await DocumentDAO.list_by_user(db, user_id)
        return [self._to_dict(d) for d in docs]

    async def delete_document(self, db: AsyncSession, user_id: uuid.UUID, doc_id: int) -> bool:
        doc = await DocumentDAO.get_by_id_and_user(db, doc_id, user_id)
        if not doc:
            return False
        await DocumentChunkDAO.delete_by_document(db, doc_id)
        await DocumentDAO.delete(db, doc)
        return True

    # ---- 语义检索 ----
    async def search(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        query: str,
        limit: int = 5,
    ) -> List[dict]:
        docs = await DocumentDAO.list_by_user(db, user_id)
        ready_ids = [d.id for d in docs if d.status == "ready"]
        if not ready_ids or not query.strip():
            return []
        query_vec = await self.embedder.embed(query)
        chunks = await DocumentChunkDAO.list_similar(db, ready_ids, query_vec, limit=limit)
        return [
            {"content": c.content, "document_id": c.document_id, "score_index": i}
            for i, c in enumerate(chunks)
        ]

    # ---- RAG 问答 ----
    async def rag_answer(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        query: str,
        llm: Optional[LLMClient] = None,
    ) -> dict:
        hits = await self.search(db, user_id, query, limit=4)
        if not hits:
            return {"answer": "你的知识库里还没有相关内容，请先上传文档或换个问题试试。", "sources": []}

        context = "\n\n".join(f"[资料{i+1}] {h['content']}" for i, h in enumerate(hits))
        system_prompt = (
            "你是 Lunaris 的文档答疑助手。请仅依据提供的知识库资料回答用户问题，"
            "若资料不足以回答，请明确说明。回答需清晰、有条理，可适当引用资料。"
        )
        user_prompt = f"【知识库资料】\n{context}\n\n【用户问题】\n{query}"
        client = llm or LLMClient()
        try:
            answer = await client.chat_completion(
                system_prompt=system_prompt,
                history=[],
                user_message=user_prompt,
                temperature=0.3,
                max_tokens=800,
            )
        except Exception:
            # LLM 不可用时回退到只返回检索结果
            answer = "（AI 摘要不可用，以下为命中的知识库片段）\n" + "\n".join(
                h["content"] for h in hits
            )
        return {
            "answer": answer,
            "sources": [{"content": h["content"], "document_id": h["document_id"]} for h in hits],
        }

    def _to_dict(self, d: Document) -> dict:
        return {
            "id": d.id,
            "file_name": d.file_name,
            "file_type": d.file_type,
            "file_size": d.file_size,
            "file_url": d.file_url,
            "status": d.status,
            "chunk_count": d.chunk_count,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }


# 全局单例
_knowledge_service = None


def get_knowledge_service() -> KnowledgeService:
    global _knowledge_service
    if _knowledge_service is None:
        _knowledge_service = KnowledgeService()
    return _knowledge_service