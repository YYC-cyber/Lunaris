# backend/controllers/knowledge_controller.py
"""知识库（RAG）控制器 —— 文档上传、列表、删除、语义检索、RAG 问答。"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from middleware.auth_middleware import get_current_user
from models.user import User
from services.knowledge_service import get_knowledge_service

router = APIRouter()


@router.post("/documents")
async def upload_document(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """上传文档到知识库（自动分块 + 向量化）。"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名为空")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="空文件")
    try:
        doc = await get_knowledge_service().upload(db, user.id, file.filename, content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"document": doc.id, "status": doc.status, "chunk_count": doc.chunk_count}


@router.get("/documents")
async def list_documents(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """列出当前用户知识库的全部文档。"""
    docs = await get_knowledge_service().list_documents(db, user.id)
    return {"documents": docs}


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除某篇文档及其全部分块。"""
    ok = await get_knowledge_service().delete_document(db, user.id, doc_id)
    if not ok:
        raise HTTPException(status_code=404, detail="文档不存在")
    return {"deleted": True}


@router.get("/search")
async def search_documents(
    query: str = Query(..., min_length=1),
    limit: int = Query(5, ge=1, le=10),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """语义检索：返回知识库中与 query 最相关的分块。"""
    hits = await get_knowledge_service().search(db, user.id, query, limit=limit)
    return {"results": hits}


@router.post("/ask")
async def rag_answer(
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """RAG 问答：检索知识库并生成有依据的回答。"""
    query = (body.get("query") or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="query 不能为空")
    result = await get_knowledge_service().rag_answer(db, user.id, query)
    return result