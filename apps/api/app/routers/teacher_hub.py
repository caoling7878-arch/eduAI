from __future__ import annotations

"""教师工作台聚合：课程、进度、背单词打卡、学情、批改、备课入口数据。"""

from collections import defaultdict
from datetime import date
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import (
    Checkin,
    ClassMember,
    ClassRoom,
    Course,
    GradeTask,
    Paper,
    ProgressItem,
    Submission,
    User,
    VocabDailyLog,
    VocabReward,
    WrongItem,
)
from ..rbac import require_staff

router = APIRouter(prefix="/teacher", tags=["teacher"])


class WeakPointOut(BaseModel):
    knowledge_point: str
    wrong_count: int


class CourseBlockOut(BaseModel):
    id: int
    title: str
    status: str = "draft"
    summary: str = ""
    class_count: int = 0
    class_names: List[str] = Field(default_factory=list)
    student_count: int = 0


class ClassProgressOut(BaseModel):
    id: int
    name: str
    course_id: Optional[int] = None
    course_title: str = ""
    student_count: int = 0
    progress_completed_avg: float = 0
    avg_score_rate: float = 0
    pending_grades: int = 0
    vocab_today_done: int = 0
    vocab_today_total: int = 0
    vocab_rate: float = 0


class StudentProgressOut(BaseModel):
    user_id: int
    display_name: str
    class_name: str
    progress_completed: int = 0
    avg_score_rate: float = 0
    wrong_open: int = 0
    pending_grades: int = 0
    vocab_today: bool = False
    streak_days: int = 0


class VocabCheckinOut(BaseModel):
    user_id: int
    display_name: str
    class_name: str
    completed: bool = False
    stars_earned: int = 0
    streak_days: int = 0
    bank: str = ""


class TeacherHubOut(BaseModel):
    teacher_name: str
    summary: dict
    courses: List[CourseBlockOut]
    classes: List[ClassProgressOut]
    students: List[StudentProgressOut]
    vocab_checkins: List[VocabCheckinOut]
    weak_points: List[WeakPointOut]
    grade_pending: int = 0


class ProgressHistoryItem(BaseModel):
    course_id: str
    item_id: str
    status: str
    score: int = 0
    updated_at: Optional[str] = None


class SubmissionHistoryItem(BaseModel):
    id: int
    paper_id: int
    paper_title: str = ""
    score: float = 0
    total: float = 0
    rate: float = 0
    created_at: Optional[str] = None


class VocabHistoryItem(BaseModel):
    day: str
    bank: str = ""
    completed: bool = False
    new_count: int = 0
    review_count: int = 0
    quiz_total: int = 0
    quiz_correct: int = 0
    stars_earned: int = 0


class WrongHistoryItem(BaseModel):
    id: int
    knowledge_points: str = ""
    source: str = ""
    mastered: bool = False
    user_answer: str = ""
    correct_answer: str = ""
    created_at: Optional[str] = None


class CheckinHistoryItem(BaseModel):
    day: str


class StudentHistoryOut(BaseModel):
    user_id: int
    display_name: str
    email: str = ""
    class_names: List[str] = Field(default_factory=list)
    summary: dict
    progress: List[ProgressHistoryItem] = Field(default_factory=list)
    submissions: List[SubmissionHistoryItem] = Field(default_factory=list)
    vocab_logs: List[VocabHistoryItem] = Field(default_factory=list)
    wrong_items: List[WrongHistoryItem] = Field(default_factory=list)
    checkins: List[CheckinHistoryItem] = Field(default_factory=list)


def _teacher_classes(db: Session, user: User) -> List[ClassRoom]:
    stmt = select(ClassRoom).order_by(ClassRoom.id.desc())
    if user.role == "teacher":
        stmt = stmt.where(ClassRoom.teacher_id == user.id)
    return list(db.scalars(stmt))


def _student_member_ids(db: Session, class_ids: List[int]) -> tuple[Dict[int, List[int]], List[int]]:
    """只统计学员角色成员，排除教师本人等非学生账号。"""
    members_by_class: Dict[int, List[int]] = defaultdict(list)
    all_member_ids: List[int] = []
    if not class_ids:
        return members_by_class, all_member_ids
    rows = db.execute(
        select(ClassMember.user_id, ClassMember.class_id, User.role)
        .join(User, User.id == ClassMember.user_id)
        .where(ClassMember.class_id.in_(class_ids), User.role == "student")
    ).all()
    for mid, cid, _role in rows:
        members_by_class[int(cid)].append(int(mid))
        all_member_ids.append(int(mid))
    return members_by_class, list(dict.fromkeys(all_member_ids))


def _ensure_teacher_can_view_student(db: Session, staff: User, student_id: int) -> User:
    student = db.get(User, student_id)
    if not student or student.role != "student":
        raise HTTPException(status_code=404, detail="学员不存在")
    if staff.role == "admin":
        return student
    class_ids = [c.id for c in _teacher_classes(db, staff)]
    if not class_ids:
        raise HTTPException(status_code=403, detail="无权查看该学员")
    ok = db.scalar(
        select(ClassMember.id).where(
            ClassMember.class_id.in_(class_ids), ClassMember.user_id == student_id
        )
    )
    if not ok:
        raise HTTPException(status_code=403, detail="只能查看自己班级学员的学情")
    return student


@router.get("/students/{student_id}/history", response_model=StudentHistoryOut)
def student_learning_history(
    student_id: int,
    staff: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> StudentHistoryOut:
    """教师查看班级学员的学习历史（进度/交卷/背单词/错题/打卡）。"""
    student = _ensure_teacher_can_view_student(db, staff, student_id)
    classes = _teacher_classes(db, staff)
    class_names = []
    for c in classes:
        hit = db.scalar(
            select(ClassMember.id).where(ClassMember.class_id == c.id, ClassMember.user_id == student_id)
        )
        if hit:
            class_names.append(c.name)

    progress_rows = list(
        db.scalars(
            select(ProgressItem)
            .where(ProgressItem.user_id == student_id)
            .order_by(ProgressItem.updated_at.desc())
            .limit(200)
        )
    )
    progress = [
        ProgressHistoryItem(
            course_id=p.course_id,
            item_id=p.item_id,
            status=p.status,
            score=int(p.score or 0),
            updated_at=p.updated_at.isoformat() if p.updated_at else None,
        )
        for p in progress_rows
    ]

    papers = {p.id: p for p in db.scalars(select(Paper))}
    subs = list(
        db.scalars(
            select(Submission)
            .where(Submission.user_id == student_id)
            .order_by(Submission.created_at.desc())
            .limit(100)
        )
    )
    submissions = []
    for s in subs:
        rate = round((s.score / s.total) * 100, 1) if s.total else 0.0
        paper = papers.get(s.paper_id)
        submissions.append(
            SubmissionHistoryItem(
                id=s.id,
                paper_id=s.paper_id,
                paper_title=paper.title if paper else f"试卷#{s.paper_id}",
                score=float(s.score or 0),
                total=float(s.total or 0),
                rate=rate,
                created_at=s.created_at.isoformat() if s.created_at else None,
            )
        )

    vocab_rows = list(
        db.scalars(
            select(VocabDailyLog)
            .where(VocabDailyLog.user_id == student_id)
            .order_by(VocabDailyLog.day.desc())
            .limit(60)
        )
    )
    vocab_logs = [
        VocabHistoryItem(
            day=v.day,
            bank=v.bank or "",
            completed=bool(v.completed),
            new_count=int(v.new_count or 0),
            review_count=int(v.review_count or 0),
            quiz_total=int(v.quiz_total or 0),
            quiz_correct=int(v.quiz_correct or 0),
            stars_earned=int(v.stars_earned or 0),
        )
        for v in vocab_rows
    ]

    wrongs = list(
        db.scalars(
            select(WrongItem)
            .where(WrongItem.user_id == student_id)
            .order_by(WrongItem.created_at.desc())
            .limit(100)
        )
    )
    wrong_items = [
        WrongHistoryItem(
            id=w.id,
            knowledge_points=w.knowledge_points or "",
            source=w.source or "",
            mastered=bool(w.mastered),
            user_answer=(w.user_answer or "")[:120],
            correct_answer=(w.correct_answer or "")[:120],
            created_at=w.created_at.isoformat() if w.created_at else None,
        )
        for w in wrongs
    ]

    checkin_rows = list(
        db.scalars(
            select(Checkin).where(Checkin.user_id == student_id).order_by(Checkin.day.desc()).limit(60)
        )
    )
    checkins = [CheckinHistoryItem(day=c.day) for c in checkin_rows]

    reward = db.scalar(select(VocabReward).where(VocabReward.user_id == student_id))
    completed_n = sum(1 for p in progress_rows if p.status == "completed")
    wrong_open = sum(1 for w in wrongs if not w.mastered)
    avg_rate = round(sum(s.rate for s in submissions) / len(submissions), 1) if submissions else 0.0

    return StudentHistoryOut(
        user_id=student.id,
        display_name=student.display_name or student.email,
        email=student.email,
        class_names=class_names,
        summary={
            "progress_completed": completed_n,
            "progress_total": len(progress_rows),
            "submissions": len(submissions),
            "avg_score_rate": avg_rate,
            "wrong_open": wrong_open,
            "wrong_total": len(wrong_items),
            "vocab_days": len(vocab_logs),
            "vocab_completed_days": sum(1 for v in vocab_logs if v.completed),
            "checkins": len(checkins),
            "streak_days": int(reward.streak_days or 0) if reward else 0,
        },
        progress=progress,
        submissions=submissions,
        vocab_logs=vocab_logs,
        wrong_items=wrong_items,
        checkins=checkins,
    )


@router.get("/hub", response_model=TeacherHubOut)
def teacher_hub(user: User = Depends(require_staff), db: Session = Depends(get_db)) -> TeacherHubOut:
    today = date.today().isoformat()
    classes = _teacher_classes(db, user)
    class_ids = [c.id for c in classes]
    members_by_class, all_member_ids = _student_member_ids(db, class_ids)

    users = {
        u.id: u
        for u in (
            list(db.scalars(select(User).where(User.id.in_(all_member_ids)))) if all_member_ids else []
        )
    }

    progress_by: Dict[int, int] = defaultdict(int)
    if all_member_ids:
        for uid, n in db.execute(
            select(ProgressItem.user_id, func.count())
            .where(ProgressItem.user_id.in_(all_member_ids), ProgressItem.status == "completed")
            .group_by(ProgressItem.user_id)
        ):
            progress_by[int(uid)] = int(n)

    subs_by: Dict[int, List[Submission]] = defaultdict(list)
    if all_member_ids:
        for s in db.scalars(select(Submission).where(Submission.user_id.in_(all_member_ids))):
            subs_by[s.user_id].append(s)

    def score_rate(uid: int) -> float:
        rows = subs_by.get(uid) or []
        if not rows:
            return 0.0
        rates = [(x.score / x.total) if x.total else 0 for x in rows]
        return round(sum(rates) / len(rates) * 100, 1)

    wrong_open_by: Dict[int, int] = defaultdict(int)
    kp_all: Dict[str, int] = defaultdict(int)
    if all_member_ids:
        for w in db.scalars(select(WrongItem).where(WrongItem.user_id.in_(all_member_ids))):
            if w.mastered:
                continue
            wrong_open_by[w.user_id] += 1
            key = (w.knowledge_points or "未标注").split(",")[0].strip() or "未标注"
            kp_all[key] += 1

    pending_by: Dict[int, int] = defaultdict(int)
    grade_pending = 0
    if all_member_ids:
        for uid, n in db.execute(
            select(GradeTask.user_id, func.count())
            .where(
                GradeTask.user_id.in_(all_member_ids),
                GradeTask.status.in_(["pending", "ai_scored"]),
            )
            .group_by(GradeTask.user_id)
        ):
            pending_by[int(uid)] = int(n)
            grade_pending += int(n)
    elif user.role == "admin":
        grade_pending = int(
            db.scalar(
                select(func.count())
                .select_from(GradeTask)
                .where(GradeTask.status.in_(["pending", "ai_scored"]))
            )
            or 0
        )

    vocab_logs = {
        int(r.user_id): r
        for r in (
            list(
                db.scalars(
                    select(VocabDailyLog).where(
                        VocabDailyLog.user_id.in_(all_member_ids), VocabDailyLog.day == today
                    )
                )
            )
            if all_member_ids
            else []
        )
    }
    rewards = {
        int(r.user_id): r
        for r in (
            list(db.scalars(select(VocabReward).where(VocabReward.user_id.in_(all_member_ids))))
            if all_member_ids
            else []
        )
    }

    course_ids = [c.course_id for c in classes if c.course_id]
    if user.role == "admin":
        course_rows = list(db.scalars(select(Course).order_by(Course.sort_order, Course.id.desc()).limit(40)))
    else:
        if course_ids:
            course_rows = list(
                db.scalars(select(Course).where(Course.id.in_(list(dict.fromkeys(course_ids)))))
            )
        else:
            course_rows = list(
                db.scalars(
                    select(Course)
                    .where(Course.status == "published")
                    .order_by(Course.sort_order, Course.id.desc())
                    .limit(20)
                )
            )
    courses_by_id = {c.id: c for c in course_rows}

    class_outs: List[ClassProgressOut] = []
    for c in classes:
        mids = members_by_class.get(c.id, [])
        n = len(mids)
        prog_avg = round(sum(progress_by.get(uid, 0) for uid in mids) / n, 1) if n else 0.0
        score_avg = round(sum(score_rate(uid) for uid in mids) / n, 1) if n else 0.0
        pending = sum(pending_by.get(uid, 0) for uid in mids)
        v_done = sum(1 for uid in mids if vocab_logs.get(uid) and vocab_logs[uid].completed)
        course = courses_by_id.get(c.course_id) if c.course_id else None
        class_outs.append(
            ClassProgressOut(
                id=c.id,
                name=c.name,
                course_id=c.course_id,
                course_title=course.title if course else "",
                student_count=n,
                progress_completed_avg=prog_avg,
                avg_score_rate=score_avg,
                pending_grades=pending,
                vocab_today_done=v_done,
                vocab_today_total=n,
                vocab_rate=round(v_done * 100 / n, 1) if n else 0.0,
            )
        )

    classes_by_course: Dict[Optional[int], List[ClassRoom]] = defaultdict(list)
    for c in classes:
        classes_by_course[c.course_id].append(c)

    course_blocks: List[CourseBlockOut] = []
    seen_course = set()
    for course in course_rows:
        seen_course.add(course.id)
        linked = classes_by_course.get(course.id, [])
        mids: List[int] = []
        for cl in linked:
            mids.extend(members_by_class.get(cl.id, []))
        course_blocks.append(
            CourseBlockOut(
                id=course.id,
                title=course.title,
                status=course.status,
                summary=(course.summary or "")[:120],
                class_count=len(linked),
                class_names=[cl.name for cl in linked],
                student_count=len(dict.fromkeys(mids)),
            )
        )
    for cid, linked in classes_by_course.items():
        if not cid or cid in seen_course:
            continue
        course = db.get(Course, cid)
        if not course:
            continue
        mids = []
        for cl in linked:
            mids.extend(members_by_class.get(cl.id, []))
        course_blocks.append(
            CourseBlockOut(
                id=course.id,
                title=course.title,
                status=course.status,
                summary=(course.summary or "")[:120],
                class_count=len(linked),
                class_names=[cl.name for cl in linked],
                student_count=len(dict.fromkeys(mids)),
            )
        )

    class_name_of: Dict[int, str] = {}
    for c in classes:
        for uid in members_by_class.get(c.id, []):
            class_name_of.setdefault(uid, c.name)

    students: List[StudentProgressOut] = []
    for uid in all_member_ids:
        u = users.get(uid)
        if not u:
            continue
        log = vocab_logs.get(uid)
        reward = rewards.get(uid)
        students.append(
            StudentProgressOut(
                user_id=uid,
                display_name=u.display_name or u.email,
                class_name=class_name_of.get(uid, ""),
                progress_completed=progress_by.get(uid, 0),
                avg_score_rate=score_rate(uid),
                wrong_open=wrong_open_by.get(uid, 0),
                pending_grades=pending_by.get(uid, 0),
                vocab_today=bool(log and log.completed),
                streak_days=int(reward.streak_days or 0) if reward else 0,
            )
        )
    students.sort(
        key=lambda s: (
            -(1 if not s.vocab_today else 0),
            -s.pending_grades,
            -s.wrong_open,
            -s.progress_completed,
        )
    )

    vocab_checkins: List[VocabCheckinOut] = []
    for uid in all_member_ids:
        u = users.get(uid)
        if not u:
            continue
        log = vocab_logs.get(uid)
        reward = rewards.get(uid)
        vocab_checkins.append(
            VocabCheckinOut(
                user_id=uid,
                display_name=u.display_name or u.email,
                class_name=class_name_of.get(uid, ""),
                completed=bool(log and log.completed),
                stars_earned=int(log.stars_earned or 0) if log else 0,
                streak_days=int(reward.streak_days or 0) if reward else 0,
                bank=(log.bank if log else "") or "",
            )
        )
    vocab_checkins.sort(key=lambda x: (x.completed, -x.streak_days, x.display_name))

    weak_points = [
        WeakPointOut(knowledge_point=k, wrong_count=v)
        for k, v in sorted(kp_all.items(), key=lambda x: -x[1])[:8]
    ]

    vocab_done = sum(1 for v in vocab_checkins if v.completed)
    vocab_total = len(vocab_checkins)
    avg_progress = (
        round(sum(s.progress_completed for s in students) / len(students), 1) if students else 0.0
    )
    avg_score = round(sum(s.avg_score_rate for s in students) / len(students), 1) if students else 0.0

    return TeacherHubOut(
        teacher_name=user.display_name or user.email,
        summary={
            "class_count": len(classes),
            "student_count": len(all_member_ids),
            "course_count": len(course_blocks),
            "grade_pending": grade_pending,
            "vocab_done_today": vocab_done,
            "vocab_total_today": vocab_total,
            "vocab_rate": round(vocab_done * 100 / vocab_total, 1) if vocab_total else 0.0,
            "avg_progress_completed": avg_progress,
            "avg_score_rate": avg_score,
            "wrong_open_total": sum(wrong_open_by.values()),
        },
        courses=course_blocks,
        classes=class_outs,
        students=students[:40],
        vocab_checkins=vocab_checkins[:60],
        weak_points=weak_points,
        grade_pending=grade_pending,
    )
