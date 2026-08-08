from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..db import get_db
from ..models import Question, User, WrongItem

router = APIRouter(prefix="/wrongbook", tags=["wrongbook"])


class WrongOut(BaseModel):
    id: int
    question_id: int
    paper_id: Optional[int]
    stem: str
    user_answer: str
    correct_answer: str
    analysis: str
    knowledge_points: str
    source: str
    mastered: bool
    created_at: Optional[str] = None


@router.get("", response_model=List[WrongOut])
def list_wrong(
    mastered: Optional[bool] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[WrongOut]:
    stmt = select(WrongItem).where(WrongItem.user_id == user.id).order_by(WrongItem.id.desc())
    if mastered is not None:
        stmt = stmt.where(WrongItem.mastered.is_(mastered))
    out: List[WrongOut] = []
    for w in db.scalars(stmt):
        q = db.get(Question, w.question_id)
        out.append(
            WrongOut(
                id=w.id,
                question_id=w.question_id,
                paper_id=w.paper_id,
                stem=q.stem if q else "",
                user_answer=w.user_answer,
                correct_answer=w.correct_answer,
                analysis=q.analysis if q else "",
                knowledge_points=w.knowledge_points,
                source=w.source,
                mastered=w.mastered,
                created_at=w.created_at.isoformat() if w.created_at else None,
            )
        )
    return out


@router.post("/{wid}/master")
def mark_mastered(
    wid: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    w = db.get(WrongItem, wid)
    if not w or w.user_id != user.id:
        raise HTTPException(status_code=404, detail="错题不存在")
    w.mastered = True
    db.commit()
    return {"status": "ok"}


@router.delete("/{wid}")
def delete_wrong(
    wid: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    w = db.get(WrongItem, wid)
    if not w or w.user_id != user.id:
        raise HTTPException(status_code=404, detail="错题不存在")
    db.delete(w)
    db.commit()
    return {"status": "ok"}
