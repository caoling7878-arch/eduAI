from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit_util import write_audit
from ..db import get_db
from ..models import ClassMember, ClassRoom, User
from ..rbac import require_staff
from ..schemas import ClassIn, ClassOut
from ..services.teacher_scope import assert_teacher_owns_class, filter_member_ids_for_teacher


router = APIRouter(prefix="/classes", tags=["classes"])


def _out(db: Session, c: ClassRoom) -> ClassOut:
    mids = list(
        db.scalars(
            select(ClassMember.user_id)
            .join(User, User.id == ClassMember.user_id)
            .where(ClassMember.class_id == c.id, User.role == "student")
        )
    )
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
    member_ids = filter_member_ids_for_teacher(db, admin, list(body.member_ids or []))
    c = ClassRoom(name=body.name, teacher_id=teacher_id, course_id=body.course_id)
    db.add(c)
    db.flush()
    for uid in member_ids:
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
    c = assert_teacher_owns_class(db, admin, class_id)
    c.name = body.name
    if admin.role == "admin":
        c.teacher_id = body.teacher_id
    c.course_id = body.course_id
    member_ids = filter_member_ids_for_teacher(db, admin, list(body.member_ids or []))
    # 更新时允许保留本班现有学员（即使按「全局已任教池」校验也在池内）
    for m in list(db.scalars(select(ClassMember).where(ClassMember.class_id == class_id))):
        db.delete(m)
    for uid in member_ids:
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
    c = assert_teacher_owns_class(db, admin, class_id)
    db.delete(c)
    write_audit(db, user=admin, action="class.delete", resource=str(class_id))
    db.commit()
    return {"status": "ok"}
