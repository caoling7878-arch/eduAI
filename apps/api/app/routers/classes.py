from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit_util import write_audit
from ..db import get_db
from ..models import ClassMember, ClassRoom, User
from ..rbac import require_staff
from ..schemas import ClassIn, ClassOut

router = APIRouter(prefix="/classes", tags=["classes"])


def _out(db: Session, c: ClassRoom) -> ClassOut:
    mids = list(db.scalars(select(ClassMember.user_id).where(ClassMember.class_id == c.id)))
    return ClassOut(
        id=c.id,
        name=c.name,
        teacher_id=c.teacher_id,
        course_id=c.course_id,
        member_ids=mids,
        created_at=c.created_at,
    )


@router.get("", response_model=list[ClassOut])
def list_classes(
    mine: bool = False,
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> list[ClassOut]:
    stmt = select(ClassRoom).order_by(ClassRoom.id.desc())
    # 教师默认只看自己的班；管理员看全部。mine=true 强制按当前用户过滤。
    if user.role == "teacher" or mine:
        stmt = stmt.where(ClassRoom.teacher_id == user.id)
    rows = list(db.scalars(stmt))
    return [_out(db, c) for c in rows]


@router.post("", response_model=ClassOut)
def create_class(
    body: ClassIn,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> ClassOut:
    teacher_id = body.teacher_id
    if admin.role == "teacher":
        teacher_id = admin.id
    c = ClassRoom(name=body.name, teacher_id=teacher_id, course_id=body.course_id)
    db.add(c)
    db.flush()
    for uid in body.member_ids:
        db.add(ClassMember(class_id=c.id, user_id=uid))
    write_audit(db, user=admin, action="class.create", resource=body.name)
    db.commit()
    db.refresh(c)
    return _out(db, c)


@router.patch("/{class_id}", response_model=ClassOut)
def update_class(
    class_id: int,
    body: ClassIn,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> ClassOut:
    c = db.get(ClassRoom, class_id)
    if not c:
        raise HTTPException(status_code=404, detail="班级不存在")
    if admin.role == "teacher" and c.teacher_id != admin.id:
        raise HTTPException(status_code=403, detail="只能管理自己的班级")
    c.name = body.name
    if admin.role == "admin":
        c.teacher_id = body.teacher_id
    c.course_id = body.course_id
    for m in list(db.scalars(select(ClassMember).where(ClassMember.class_id == class_id))):
        db.delete(m)
    for uid in body.member_ids:
        db.add(ClassMember(class_id=class_id, user_id=uid))
    write_audit(db, user=admin, action="class.update", resource=str(class_id))
    db.commit()
    db.refresh(c)
    return _out(db, c)


@router.delete("/{class_id}")
def delete_class(
    class_id: int,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    c = db.get(ClassRoom, class_id)
    if not c:
        raise HTTPException(status_code=404, detail="班级不存在")
    if admin.role == "teacher" and c.teacher_id != admin.id:
        raise HTTPException(status_code=403, detail="只能管理自己的班级")
    db.delete(c)
    write_audit(db, user=admin, action="class.delete", resource=str(class_id))
    db.commit()
    return {"status": "ok"}
