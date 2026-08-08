from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit_util import write_audit
from ..db import get_db
from ..models import TeacherProfile, User
from ..rbac import require_admin, require_staff
from ..schemas import TeacherIn, TeacherOut

router = APIRouter(prefix="/teachers", tags=["teachers"])


def _out(p: TeacherProfile, u: User) -> TeacherOut:
    return TeacherOut(
        id=p.id,
        user_id=p.user_id,
        display_name=u.display_name,
        email=u.email,
        title=p.title,
        bio=p.bio,
        subjects=p.subjects,
    )


@router.get("", response_model=list[TeacherOut])
def list_teachers(_: User = Depends(require_staff), db: Session = Depends(get_db)) -> list[TeacherOut]:
    rows = db.execute(
        select(TeacherProfile, User).join(User, User.id == TeacherProfile.user_id)
    ).all()
    return [_out(p, u) for p, u in rows]


@router.post("", response_model=TeacherOut)
def upsert_teacher(
    body: TeacherIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> TeacherOut:
    u = db.get(User, body.user_id)
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    u.role = "teacher"
    p = db.scalar(select(TeacherProfile).where(TeacherProfile.user_id == body.user_id))
    if p is None:
        p = TeacherProfile(user_id=body.user_id)
        db.add(p)
    p.title = body.title
    p.bio = body.bio
    p.subjects = body.subjects
    write_audit(db, user=admin, action="teacher.upsert", resource=str(body.user_id))
    db.commit()
    db.refresh(p)
    return _out(p, u)
