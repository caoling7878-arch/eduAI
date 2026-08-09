from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..audit_util import write_audit
from ..db import get_db
from ..models import KnowledgeBase, KnowledgeChunk, KnowledgeDoc, User
from ..rbac import require_admin, require_staff
from ..schemas import (
    KbGenerateCourseIn,
    KbGenerateQuestionsIn,
    KnowledgeBaseIn,
    KnowledgeBaseOut,
    KnowledgeDocIn,
    KnowledgeDocOut,
)
from ..services.doc_parse import SUPPORTED_EXTENSIONS, parse_upload
from ..services.embeddings import save_embedding_config
from ..services.kb_generate import generate_course_from_kb, generate_questions_from_kb
from ..services.rag import (
    embedding_config_public,
    embedding_status,
    index_document,
    reindex_kb,
    retrieve_docs,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class SearchIn(BaseModel):
    kb_id: int
    query: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=5, ge=1, le=20)


class EmbeddingConfigIn(BaseModel):
    mode: str = Field(default="auto", pattern="^(auto|api|hash)$")
    base_url: str = ""
    api_key: Optional[str] = None  # None=不修改；""=清空
    model: str = "text-embedding-3-small"


def _doc_out(d: KnowledgeDoc) -> KnowledgeDocOut:
    return KnowledgeDocOut(
        id=d.id,
        kb_id=d.kb_id,
        title=d.title,
        content=d.content or "",
        status=d.status or "ready",
        source_filename=getattr(d, "source_filename", None) or "",
        source_type=getattr(d, "source_type", None) or "text",
    )


@router.get("/embedding-status")
def get_embedding_status(
    probe: bool = False,
    _: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> dict:
    return embedding_status(db, probe=probe)


@router.get("/embedding-config")
def get_embedding_config_api(
    _: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> dict:
    return embedding_config_public(db)


@router.put("/embedding-config")
def put_embedding_config_api(
    body: EmbeddingConfigIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    save_embedding_config(
        db,
        mode=body.mode,
        base_url=body.base_url,
        api_key=body.api_key,
        model=body.model,
    )
    write_audit(
        db,
        user=admin,
        action="knowledge.embedding_config",
        resource="embedding",
        detail=f"mode={body.mode} model={body.model}",
    )
    status = embedding_status(db, probe=body.mode != "hash")
    return {"config": embedding_config_public(db), "status": status}


@router.get("/bases", response_model=list[KnowledgeBaseOut])
def list_bases(_: User = Depends(require_staff), db: Session = Depends(get_db)) -> list[KnowledgeBaseOut]:
    bases = list(db.scalars(select(KnowledgeBase).order_by(KnowledgeBase.id)))
    out: list[KnowledgeBaseOut] = []
    for b in bases:
        n = db.scalar(select(func.count()).select_from(KnowledgeDoc).where(KnowledgeDoc.kb_id == b.id)) or 0
        chunks = db.scalar(select(func.count()).select_from(KnowledgeChunk).where(KnowledgeChunk.kb_id == b.id)) or 0
        out.append(
            KnowledgeBaseOut(
                id=b.id,
                name=b.name,
                description=b.description,
                doc_count=int(n),
                chunk_count=int(chunks),
            )
        )
    return out


@router.post("/bases", response_model=KnowledgeBaseOut)
def create_base(
    body: KnowledgeBaseIn,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> KnowledgeBaseOut:
    b = KnowledgeBase(name=body.name, description=body.description)
    db.add(b)
    write_audit(db, user=admin, action="kb.create", resource=body.name)
    db.commit()
    db.refresh(b)
    return KnowledgeBaseOut(id=b.id, name=b.name, description=b.description, doc_count=0)


@router.get("/bases/{kb_id}/docs", response_model=list[KnowledgeDocOut])
def list_docs(
    kb_id: int,
    _: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> list[KnowledgeDocOut]:
    rows = list(db.scalars(select(KnowledgeDoc).where(KnowledgeDoc.kb_id == kb_id)))
    return [_doc_out(d) for d in rows]


@router.post("/bases/{kb_id}/docs", response_model=KnowledgeDocOut)
def add_doc(
    kb_id: int,
    body: KnowledgeDocIn,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> KnowledgeDocOut:
    if not db.get(KnowledgeBase, kb_id):
        raise HTTPException(status_code=404, detail="知识库不存在")
    d = KnowledgeDoc(
        kb_id=kb_id,
        title=body.title,
        content=body.content,
        status="indexing",
        source_type="text",
        source_filename="",
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    info = index_document(db, d)
    write_audit(
        db,
        user=admin,
        action="kb.doc.create",
        resource=body.title,
        detail=str(info),
    )
    db.commit()
    db.refresh(d)
    return _doc_out(d)


@router.post("/bases/{kb_id}/upload", response_model=KnowledgeDocOut)
async def upload_doc(
    kb_id: int,
    file: UploadFile = File(...),
    title: Optional[str] = Form(default=None),
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> KnowledgeDocOut:
    if not db.get(KnowledgeBase, kb_id):
        raise HTTPException(status_code=404, detail="知识库不存在")
    filename = file.filename or "upload.bin"
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的格式 {ext or '(无扩展名)'}，请上传 PDF / MD / TXT / DOCX",
        )
    data = await file.read()
    try:
        source_type, text = parse_upload(filename, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    doc_title = (title or "").strip() or Path(filename).stem or "未命名教材"
    d = KnowledgeDoc(
        kb_id=kb_id,
        title=doc_title[:200],
        content=text,
        status="indexing",
        source_filename=filename[:255],
        source_type=source_type,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    try:
        info = index_document(db, d)
    except Exception as e:
        d.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"索引失败：{e}") from e
    write_audit(
        db,
        user=admin,
        action="kb.doc.upload",
        resource=doc_title,
        detail=str({"file": filename, "type": source_type, **info}),
    )
    db.commit()
    db.refresh(d)
    return _doc_out(d)


@router.delete("/docs/{doc_id}")
def delete_doc(
    doc_id: int,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    d = db.get(KnowledgeDoc, doc_id)
    if not d:
        raise HTTPException(status_code=404, detail="文档不存在")
    db.delete(d)
    write_audit(db, user=admin, action="kb.doc.delete", resource=str(doc_id))
    db.commit()
    return {"status": "ok"}


@router.post("/bases/{kb_id}/reindex")
def reindex(
    kb_id: int,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> dict:
    if not db.get(KnowledgeBase, kb_id):
        raise HTTPException(status_code=404, detail="知识库不存在")
    result = reindex_kb(db, kb_id)
    write_audit(db, user=admin, action="kb.reindex", resource=str(kb_id), detail=str(result))
    db.commit()
    return {"status": "ok", **result}


@router.post("/search")
def search_kb(
    body: SearchIn,
    _: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> dict:
    if not db.get(KnowledgeBase, body.kb_id):
        raise HTTPException(status_code=404, detail="知识库不存在")
    items = retrieve_docs(db, body.kb_id, body.query, top_k=body.top_k)
    status = embedding_status(db)
    return {"query": body.query, "items": items, "embedding": status}


@router.post("/bases/{kb_id}/generate-questions")
async def generate_questions(
    kb_id: int,
    body: KbGenerateQuestionsIn,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> dict:
    if not db.get(KnowledgeBase, kb_id):
        raise HTTPException(status_code=404, detail="知识库不存在")
    try:
        result = await generate_questions_from_kb(
            db,
            kb_id=kb_id,
            user=admin,
            count=body.count,
            difficulty=body.difficulty,
            topic=body.topic,
            query=body.query,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    write_audit(
        db,
        user=admin,
        action="kb.generate_questions",
        resource=str(kb_id),
        detail=f"count={result.get('count')} source={result.get('source')}",
    )
    db.commit()
    return result


@router.post("/bases/{kb_id}/generate-course")
async def generate_course(
    kb_id: int,
    body: KbGenerateCourseIn,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> dict:
    if not db.get(KnowledgeBase, kb_id):
        raise HTTPException(status_code=404, detail="知识库不存在")
    try:
        result = await generate_course_from_kb(
            db,
            kb_id=kb_id,
            user=admin,
            title=body.title,
            chapter_count=body.chapter_count,
            query=body.query,
            create_assistant=body.create_assistant,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    write_audit(
        db,
        user=admin,
        action="kb.generate_course",
        resource=str(kb_id),
        detail=f"course_id={result.get('course_id')} source={result.get('source')}",
    )
    db.commit()
    return result
