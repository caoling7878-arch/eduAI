from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit_util import write_audit
from ..db import get_db
from ..models import Paper, PaperTemplate, PptTemplate, Question, User
from ..rbac import require_staff
import json

router = APIRouter(prefix="/templates", tags=["templates"])


class PaperTplIn(BaseModel):
    name: str
    description: str = ""
    question_types: str = "single,judge,essay"
    default_count: int = 10


class PaperTplOut(BaseModel):
    id: int
    name: str
    description: str
    question_types: str
    default_count: int

    model_config = {"from_attributes": True}


class PptTplIn(BaseModel):
    name: str
    theme: str = "teal"
    outline_hint: str = ""


class PptTplOut(BaseModel):
    id: int
    name: str
    theme: str
    outline_hint: str

    model_config = {"from_attributes": True}


@router.get("/papers", response_model=List[PaperTplOut])
def list_paper_tpl(_: User = Depends(require_staff), db: Session = Depends(get_db)) -> List[PaperTemplate]:
    return list(db.scalars(select(PaperTemplate).order_by(PaperTemplate.id.desc())))


@router.post("/papers", response_model=PaperTplOut)
def create_paper_tpl(
    body: PaperTplIn,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> PaperTemplate:
    row = PaperTemplate(**body.model_dump())
    db.add(row)
    write_audit(db, user=admin, action="tpl.paper.create", resource=body.name)
    db.commit()
    db.refresh(row)
    return row


@router.post("/papers/{tid}/instantiate")
def instantiate_paper(
    tid: int,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> dict:
    tpl = db.get(PaperTemplate, tid)
    if not tpl:
        raise HTTPException(status_code=404, detail="模板不存在")
    types = [t.strip() for t in tpl.question_types.split(",") if t.strip()]
    qids: List[int] = []
    for t in types:
        rows = list(db.scalars(select(Question).where(Question.type == t).limit(max(1, tpl.default_count // max(1, len(types))))))
        qids.extend(q.id for q in rows)
    qids = qids[: tpl.default_count]
    paper = Paper(title=f"{tpl.name}（生成）", status="draft", question_ids=json.dumps(qids))
    db.add(paper)
    write_audit(db, user=admin, action="tpl.paper.use", resource=str(tid))
    db.commit()
    db.refresh(paper)
    return {"paper_id": paper.id, "question_count": len(qids), "title": paper.title}


@router.get("/ppt", response_model=List[PptTplOut])
def list_ppt_tpl(_: User = Depends(require_staff), db: Session = Depends(get_db)) -> List[PptTemplate]:
    return list(db.scalars(select(PptTemplate).order_by(PptTemplate.id.desc())))


@router.post("/ppt", response_model=PptTplOut)
def create_ppt_tpl(
    body: PptTplIn,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> PptTemplate:
    row = PptTemplate(**body.model_dump())
    db.add(row)
    write_audit(db, user=admin, action="tpl.ppt.create", resource=body.name)
    db.commit()
    db.refresh(row)
    return row
