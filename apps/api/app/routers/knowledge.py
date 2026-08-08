from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..audit_util import write_audit
from ..db import get_db
from ..models import KnowledgeBase, KnowledgeChunk, KnowledgeDoc, User
from ..rbac import require_staff
from ..schemas import KnowledgeBaseIn, KnowledgeBaseOut, KnowledgeDocIn, KnowledgeDocOut
from ..services.rag import embedding_status, index_document, reindex_kb, retrieve_docs

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class SearchIn(BaseModel):
    kb_id: int
    query: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=5, ge=1, le=20)


@router.get("/embedding-status")
def get_embedding_status(
    probe: bool = False,
    _: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> dict:
    return embedding_status(db, probe=probe)


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
) -> list[KnowledgeDoc]:
    return list(db.scalars(select(KnowledgeDoc).where(KnowledgeDoc.kb_id == kb_id)))


@router.post("/bases/{kb_id}/docs", response_model=KnowledgeDocOut)
def add_doc(
    kb_id: int,
    body: KnowledgeDocIn,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> KnowledgeDoc:
    if not db.get(KnowledgeBase, kb_id):
        raise HTTPException(status_code=404, detail="知识库不存在")
    d = KnowledgeDoc(kb_id=kb_id, title=body.title, content=body.content, status="indexing")
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
    return d


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
