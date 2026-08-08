from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..db import get_db
from ..models import StudyPlan, User
from ..schemas import StudyPlanIn, StudyPlanOut

router = APIRouter(prefix="/study-plans", tags=["study-plans"])


@router.get("", response_model=list[StudyPlanOut])
def my_plans(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[StudyPlan]:
    return list(db.scalars(select(StudyPlan).where(StudyPlan.user_id == user.id).order_by(StudyPlan.id.desc())))


@router.post("", response_model=StudyPlanOut)
def add_plan(
    body: StudyPlanIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StudyPlan:
    p = StudyPlan(user_id=user.id, title=body.title.strip())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.patch("/{pid}/toggle", response_model=StudyPlanOut)
def toggle_plan(
    pid: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StudyPlan:
    p = db.get(StudyPlan, pid)
    if not p or p.user_id != user.id:
        raise HTTPException(status_code=404, detail="计划不存在")
    p.done = not p.done
    db.commit()
    db.refresh(p)
    return p


@router.delete("/{pid}")
def delete_plan(
    pid: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    p = db.get(StudyPlan, pid)
    if not p or p.user_id != user.id:
        raise HTTPException(status_code=404, detail="计划不存在")
    db.delete(p)
    db.commit()
    return {"status": "ok"}
