from __future__ import annotations

"""教师数据范围：仅能访问自己任教班级的学员。"""

from typing import List, Optional, Set

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ClassMember, ClassRoom, User


def teacher_class_ids(db: Session, user: User) -> Optional[List[int]]:
    """管理员返回 None（不限制）；教师返回自己的班级 id 列表。"""
    if user.role == "admin":
        return None
    if user.role != "teacher":
        return []
    return list(db.scalars(select(ClassRoom.id).where(ClassRoom.teacher_id == user.id)))


def teacher_student_ids(db: Session, user: User) -> Optional[List[int]]:
    """管理员返回 None；教师返回自己班级内 role=student 的学员 id（去重）。"""
    class_ids = teacher_class_ids(db, user)
    if class_ids is None:
        return None
    if not class_ids:
        return []
    return list(
        dict.fromkeys(
            int(uid)
            for uid in db.scalars(
                select(ClassMember.user_id)
                .join(User, User.id == ClassMember.user_id)
                .where(ClassMember.class_id.in_(class_ids), User.role == "student")
            )
        )
    )


def assert_teacher_owns_class(db: Session, user: User, class_id: int) -> ClassRoom:
    c = db.get(ClassRoom, class_id)
    if not c:
        raise HTTPException(status_code=404, detail="班级不存在")
    if user.role == "teacher" and c.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="只能操作自己的班级")
    return c


def assert_teacher_can_view_student(db: Session, user: User, student_id: int) -> User:
    student = db.get(User, student_id)
    if not student or student.role != "student":
        raise HTTPException(status_code=404, detail="学员不存在")
    allowed = teacher_student_ids(db, user)
    if allowed is not None and student_id not in allowed:
        raise HTTPException(status_code=403, detail="只能查看自己班级的学员")
    return student


def filter_member_ids_for_teacher(db: Session, user: User, member_ids: List[int]) -> List[int]:
    """写入花名册时只保留学员角色；教师还只能包含自己班级已有学员。"""
    ids = list(dict.fromkeys(int(x) for x in (member_ids or [])))
    if not ids:
        return []
    students = {
        int(uid)
        for uid in db.scalars(select(User.id).where(User.id.in_(ids), User.role == "student"))
    }
    if user.role != "teacher":
        return [uid for uid in ids if uid in students]

    allowed: Set[int] = set(teacher_student_ids(db, user) or [])
    kept = [uid for uid in ids if uid in allowed and uid in students]
    rejected = [uid for uid in ids if uid not in kept]
    if rejected:
        raise HTTPException(
            status_code=403,
            detail="只能添加自己班级内的学员，如需新学员请联系管理员分配到您的班级",
        )
    return kept
