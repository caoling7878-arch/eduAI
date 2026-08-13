from __future__ import annotations

import csv
import io
from collections import defaultdict
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..db import get_db
from ..models import (
    Checkin,
    ClassMember,
    ClassRoom,
    GradeTask,
    ProgressItem,
    Submission,
    User,
    WrongItem,
)
from ..rbac import require_staff

router = APIRouter(prefix="/reports", tags=["reports"])


class WeakPoint(BaseModel):
    knowledge_point: str
    wrong_count: int


class StudentReport(BaseModel):
    user_id: int
    display_name: str
    submissions: int
    avg_score_rate: float
    wrong_open: int
    wrong_mastered: int
    checkins: int
    progress_completed: int
    weak_points: List[WeakPoint]
    pending_grades: int


class ClassReport(BaseModel):
    class_id: int
    class_name: str
    student_count: int
    avg_score_rate: float
    weak_points: List[WeakPoint]
    students: List[StudentReport]


def _user_report(db: Session, user: User) -> StudentReport:
    subs = list(db.scalars(select(Submission).where(Submission.user_id == user.id)))
    rate = 0.0
    if subs:
        rates = [(s.score / s.total) if s.total else 0 for s in subs]
        rate = round(sum(rates) / len(rates) * 100, 1)

    wrongs = list(db.scalars(select(WrongItem).where(WrongItem.user_id == user.id)))
    kp: Dict[str, int] = defaultdict(int)
    for w in wrongs:
        if w.mastered:
            continue
        key = (w.knowledge_points or "未标注").split(",")[0].strip() or "未标注"
        kp[key] += 1
    weak = [WeakPoint(knowledge_point=k, wrong_count=v) for k, v in sorted(kp.items(), key=lambda x: -x[1])]

    checkins = int(
        db.scalar(select(func.count()).select_from(Checkin).where(Checkin.user_id == user.id)) or 0
    )
    completed = int(
        db.scalar(
            select(func.count())
            .select_from(ProgressItem)
            .where(ProgressItem.user_id == user.id, ProgressItem.status == "completed")
        )
        or 0
    )
    pending = int(
        db.scalar(
            select(func.count())
            .select_from(GradeTask)
            .where(GradeTask.user_id == user.id, GradeTask.status.in_(["pending", "ai_scored"]))
        )
        or 0
    )
    return StudentReport(
        user_id=user.id,
        display_name=user.display_name,
        submissions=len(subs),
        avg_score_rate=rate,
        wrong_open=sum(1 for w in wrongs if not w.mastered),
        wrong_mastered=sum(1 for w in wrongs if w.mastered),
        checkins=checkins,
        progress_completed=completed,
        weak_points=weak[:8],
        pending_grades=pending,
    )


def _build_student_report(
    user: User,
    *,
    subs: List[Submission],
    wrongs: List[WrongItem],
    checkins: int,
    completed: int,
    pending: int,
) -> StudentReport:
    rate = 0.0
    if subs:
        rates = [(s.score / s.total) if s.total else 0 for s in subs]
        rate = round(sum(rates) / len(rates) * 100, 1)
    kp: Dict[str, int] = defaultdict(int)
    for w in wrongs:
        if w.mastered:
            continue
        key = (w.knowledge_points or "未标注").split(",")[0].strip() or "未标注"
        kp[key] += 1
    weak = [WeakPoint(knowledge_point=k, wrong_count=v) for k, v in sorted(kp.items(), key=lambda x: -x[1])]
    return StudentReport(
        user_id=user.id,
        display_name=user.display_name,
        submissions=len(subs),
        avg_score_rate=rate,
        wrong_open=sum(1 for w in wrongs if not w.mastered),
        wrong_mastered=sum(1 for w in wrongs if w.mastered),
        checkins=checkins,
        progress_completed=completed,
        weak_points=weak[:8],
        pending_grades=pending,
    )


def _class_report(db: Session, class_id: int) -> ClassReport:
    c = db.get(ClassRoom, class_id)
    if not c:
        raise HTTPException(status_code=404, detail="班级不存在")
    # 仅学员，排除教师等非学生成员
    member_ids = list(
        db.scalars(
            select(ClassMember.user_id)
            .join(User, User.id == ClassMember.user_id)
            .where(ClassMember.class_id == class_id, User.role == "student")
        )
    )
    if not member_ids:
        return ClassReport(
            class_id=c.id,
            class_name=c.name,
            student_count=0,
            avg_score_rate=0.0,
            weak_points=[],
            students=[],
        )

    users = {
        u.id: u
        for u in db.scalars(select(User).where(User.id.in_(member_ids)))
    }
    subs_by: Dict[int, List[Submission]] = defaultdict(list)
    for s in db.scalars(select(Submission).where(Submission.user_id.in_(member_ids))):
        subs_by[s.user_id].append(s)
    wrongs_by: Dict[int, List[WrongItem]] = defaultdict(list)
    for w in db.scalars(select(WrongItem).where(WrongItem.user_id.in_(member_ids))):
        wrongs_by[w.user_id].append(w)

    checkin_rows = db.execute(
        select(Checkin.user_id, func.count())
        .where(Checkin.user_id.in_(member_ids))
        .group_by(Checkin.user_id)
    ).all()
    checkin_by = {int(uid): int(n) for uid, n in checkin_rows}

    progress_rows = db.execute(
        select(ProgressItem.user_id, func.count())
        .where(
            ProgressItem.user_id.in_(member_ids),
            ProgressItem.status == "completed",
        )
        .group_by(ProgressItem.user_id)
    ).all()
    progress_by = {int(uid): int(n) for uid, n in progress_rows}

    pending_rows = db.execute(
        select(GradeTask.user_id, func.count())
        .where(
            GradeTask.user_id.in_(member_ids),
            GradeTask.status.in_(["pending", "ai_scored"]),
        )
        .group_by(GradeTask.user_id)
    ).all()
    pending_by = {int(uid): int(n) for uid, n in pending_rows}

    students: List[StudentReport] = []
    kp_all: Dict[str, int] = defaultdict(int)
    rates = []
    for uid in member_ids:
        u = users.get(uid)
        if not u:
            continue
        r = _build_student_report(
            u,
            subs=subs_by.get(uid, []),
            wrongs=wrongs_by.get(uid, []),
            checkins=checkin_by.get(uid, 0),
            completed=progress_by.get(uid, 0),
            pending=pending_by.get(uid, 0),
        )
        students.append(r)
        rates.append(r.avg_score_rate)
        for w in r.weak_points:
            kp_all[w.knowledge_point] += w.wrong_count
    weak = [
        WeakPoint(knowledge_point=k, wrong_count=v)
        for k, v in sorted(kp_all.items(), key=lambda x: -x[1])
    ][:10]
    return ClassReport(
        class_id=c.id,
        class_name=c.name,
        student_count=len(students),
        avg_score_rate=round(sum(rates) / len(rates), 1) if rates else 0.0,
        weak_points=weak,
        students=students,
    )


def _csv_response(filename: str, rows: List[List[str]]) -> StreamingResponse:
    buf = io.StringIO()
    buf.write("\ufeff")  # Excel UTF-8 BOM
    writer = csv.writer(buf)
    for row in rows:
        writer.writerow(row)
    data = io.BytesIO(buf.getvalue().encode("utf-8"))
    return StreamingResponse(
        data,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/me", response_model=StudentReport)
def my_report(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> StudentReport:
    return _user_report(db, user)


@router.get("/classes/{class_id}", response_model=ClassReport)
def class_report(
    class_id: int,
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> ClassReport:
    c = db.get(ClassRoom, class_id)
    if not c:
        raise HTTPException(status_code=404, detail="班级不存在")
    if user.role == "teacher" and c.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="只能查看自己班级的学情")
    return _class_report(db, class_id)


@router.get("/classes/{class_id}/export")
def export_class_report(
    class_id: int,
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    c = db.get(ClassRoom, class_id)
    if not c:
        raise HTTPException(status_code=404, detail="班级不存在")
    if user.role == "teacher" and c.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="只能导出自己班级的学情")
    detail = _class_report(db, class_id)
    rows: List[List[str]] = [
        ["班级", detail.class_name],
        ["人数", str(detail.student_count)],
        ["平均得分率%", str(detail.avg_score_rate)],
        [],
        ["班级薄弱知识点", "错题数"],
    ]
    for w in detail.weak_points:
        rows.append([w.knowledge_point, str(w.wrong_count)])
    rows.append([])
    rows.append(["学员", "得分率%", "未掌握错题", "已掌握", "打卡", "进度完成", "待评", "薄弱点"])
    for s in detail.students:
        rows.append(
            [
                s.display_name,
                str(s.avg_score_rate),
                str(s.wrong_open),
                str(s.wrong_mastered),
                str(s.checkins),
                str(s.progress_completed),
                str(s.pending_grades),
                "、".join(w.knowledge_point for w in s.weak_points) or "-",
            ]
        )
    return _csv_response(f"class_{class_id}_report.csv", rows)


def _teacher_student_ids(db: Session, teacher_id: int) -> List[int]:
    class_ids = list(db.scalars(select(ClassRoom.id).where(ClassRoom.teacher_id == teacher_id)))
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


@router.get("/overview")
def overview(user: User = Depends(require_staff), db: Session = Depends(get_db)) -> dict:
    """管理端学情总览。教师仅看自己班级学员。"""
    student_ids: Optional[List[int]] = None
    if user.role == "teacher":
        student_ids = _teacher_student_ids(db, user.id)

    wrong_q = select(WrongItem).where(WrongItem.mastered.is_(False))
    if student_ids is not None:
        if not student_ids:
            return {
                "students": 0,
                "submissions": 0,
                "wrong_open": 0,
                "pending_grades": 0,
                "weak_points": [],
                "scope": "my_classes",
            }
        wrong_q = wrong_q.where(WrongItem.user_id.in_(student_ids))

    kp: Dict[str, int] = defaultdict(int)
    for w in db.scalars(wrong_q):
        key = (w.knowledge_points or "未标注").split(",")[0].strip() or "未标注"
        kp[key] += 1

    grade_q = select(func.count()).select_from(GradeTask).where(
        GradeTask.status.in_(["pending", "ai_scored"])
    )
    sub_q = select(func.count()).select_from(Submission)
    student_count_q = select(func.count()).select_from(User).where(User.role == "student")
    wrong_open_q = select(func.count()).select_from(WrongItem).where(WrongItem.mastered.is_(False))

    if student_ids is not None:
        grade_q = grade_q.where(GradeTask.user_id.in_(student_ids))
        sub_q = sub_q.where(Submission.user_id.in_(student_ids))
        student_count_q = select(func.count()).select_from(User).where(User.id.in_(student_ids))
        wrong_open_q = wrong_open_q.where(WrongItem.user_id.in_(student_ids))

    return {
        "students": int(db.scalar(student_count_q) or 0),
        "submissions": int(db.scalar(sub_q) or 0),
        "wrong_open": int(db.scalar(wrong_open_q) or 0),
        "pending_grades": int(db.scalar(grade_q) or 0),
        "weak_points": [
            {"knowledge_point": k, "wrong_count": v}
            for k, v in sorted(kp.items(), key=lambda x: -x[1])[:10]
        ],
        "scope": "my_classes" if user.role == "teacher" else "platform",
    }


@router.get("/overview/export")
def export_overview(user: User = Depends(require_staff), db: Session = Depends(get_db)) -> StreamingResponse:
    data = overview(user, db)
    rows: List[List[str]] = [
        ["指标", "数值"],
        ["学员数", str(data["students"])],
        ["交卷数", str(data["submissions"])],
        ["未掌握错题", str(data["wrong_open"])],
        ["待复核", str(data["pending_grades"])],
        [],
        ["薄弱知识点", "错题数"],
    ]
    for w in data["weak_points"]:
        rows.append([w["knowledge_point"], str(w["wrong_count"])])
    return _csv_response("learning_overview.csv", rows)
