from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit_util import write_audit
from ..db import get_db
from ..models import Question, User
from ..rbac import require_staff
from ..schemas import QuestionIn, QuestionOut

router = APIRouter(prefix="/questions", tags=["questions"])


def _out(q: Question) -> QuestionOut:
    try:
        options = json.loads(q.options_json or "[]")
    except json.JSONDecodeError:
        options = []
    return QuestionOut(
        id=q.id,
        type=q.type,
        stem=q.stem,
        options=options if isinstance(options, list) else [],
        answer=q.answer,
        analysis=q.analysis,
        knowledge_points=q.knowledge_points,
        difficulty=q.difficulty,
        version=q.version,
    )


@router.get("", response_model=list[QuestionOut])
def list_questions(
    q: str = Query(default=""),
    _: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> list[QuestionOut]:
    stmt = select(Question).order_by(Question.id.desc())
    if q.strip():
        stmt = stmt.where(Question.stem.contains(q.strip()))
    return [_out(r) for r in db.scalars(stmt)]


@router.post("", response_model=QuestionOut)
def create_question(
    body: QuestionIn,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> QuestionOut:
    row = Question(
        type=body.type,
        stem=body.stem,
        options_json=json.dumps(body.options, ensure_ascii=False),
        answer=body.answer,
        analysis=body.analysis,
        knowledge_points=body.knowledge_points,
        difficulty=body.difficulty,
    )
    db.add(row)
    write_audit(db, user=admin, action="question.create", resource=body.stem[:40])
    db.commit()
    db.refresh(row)
    return _out(row)


@router.patch("/{qid}", response_model=QuestionOut)
def update_question(
    qid: int,
    body: QuestionIn,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> QuestionOut:
    row = db.get(Question, qid)
    if not row:
        raise HTTPException(status_code=404, detail="题目不存在")
    row.type = body.type
    row.stem = body.stem
    row.options_json = json.dumps(body.options, ensure_ascii=False)
    row.answer = body.answer
    row.analysis = body.analysis
    row.knowledge_points = body.knowledge_points
    row.difficulty = body.difficulty
    row.version += 1
    write_audit(db, user=admin, action="question.update", resource=str(qid))
    db.commit()
    db.refresh(row)
    return _out(row)


@router.delete("/{qid}")
def delete_question(
    qid: int,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    row = db.get(Question, qid)
    if not row:
        raise HTTPException(status_code=404, detail="题目不存在")
    db.delete(row)
    write_audit(db, user=admin, action="question.delete", resource=str(qid))
    db.commit()
    return {"status": "ok"}
