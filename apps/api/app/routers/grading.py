from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit_util import write_audit
from ..auth import get_current_user
from ..db import get_db
from ..models import GradeTask, Notification, Question, User, WrongItem
from ..rbac import require_staff
from ..services.grading import ai_grade_task, final_score

router = APIRouter(prefix="/grading", tags=["grading"])


class GradeOut(BaseModel):
    id: int
    paper_id: Optional[int]
    submission_id: Optional[int]
    question_id: int
    user_id: int
    student_name: str = ""
    answer_text: str
    max_score: float
    ai_score: Optional[float]
    ai_feedback: str
    ai_confidence: float
    teacher_score: Optional[float]
    teacher_feedback: str
    status: str
    stem: str = ""
    knowledge_points: str = ""
    created_at: Optional[str] = None
    qc_status: str = "none"
    qc_note: str = ""


class ReviewIn(BaseModel):
    teacher_score: float = Field(ge=0)
    teacher_feedback: str = ""


class QcIn(BaseModel):
    result: str = Field(pattern="^(passed|failed)$")
    note: str = ""


class SampleIn(BaseModel):
    n: int = Field(default=5, ge=1, le=50)
    max_confidence: float = Field(default=0.85, ge=0, le=1)
    only_reviewed: bool = False


def _out(t: GradeTask, q: Optional[Question] = None, student: Optional[User] = None) -> GradeOut:
    return GradeOut(
        id=t.id,
        paper_id=t.paper_id,
        submission_id=t.submission_id,
        question_id=t.question_id,
        user_id=t.user_id,
        student_name=student.display_name if student else "",
        answer_text=t.answer_text,
        max_score=t.max_score,
        ai_score=t.ai_score,
        ai_feedback=t.ai_feedback,
        ai_confidence=t.ai_confidence,
        teacher_score=t.teacher_score,
        teacher_feedback=t.teacher_feedback,
        status=t.status,
        stem=q.stem if q else "",
        knowledge_points=q.knowledge_points if q else "",
        created_at=t.created_at.isoformat() if t.created_at else None,
        qc_status=getattr(t, "qc_status", None) or "none",
        qc_note=getattr(t, "qc_note", None) or "",
    )


@router.get("/queue", response_model=List[GradeOut])
def grade_queue(
    status: str = Query(default=""),
    qc: str = Query(default=""),
    _: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> List[GradeOut]:
    stmt = select(GradeTask).order_by(GradeTask.id.desc()).limit(100)
    if qc:
        stmt = stmt.where(GradeTask.qc_status == qc)
    elif status:
        stmt = stmt.where(GradeTask.status == status)
    else:
        stmt = stmt.where(GradeTask.status.in_(["pending", "ai_scored"]))
    rows = list(db.scalars(stmt))
    out = []
    for t in rows:
        out.append(_out(t, db.get(Question, t.question_id), db.get(User, t.user_id)))
    return out


@router.get("/me", response_model=List[GradeOut])
def my_grades(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> List[GradeOut]:
    rows = list(
        db.scalars(select(GradeTask).where(GradeTask.user_id == user.id).order_by(GradeTask.id.desc()))
    )
    return [_out(t, db.get(Question, t.question_id), user) for t in rows]


@router.post("/qc/sample", response_model=List[GradeOut])
def sample_for_qc(
    body: SampleIn,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> List[GradeOut]:
    """从已评任务中抽样进入质检队列（优先低置信度）。"""
    stmt = select(GradeTask).where(GradeTask.qc_status.in_(["none", ""]))
    if body.only_reviewed:
        stmt = stmt.where(GradeTask.status == "teacher_reviewed")
    else:
        stmt = stmt.where(GradeTask.status.in_(["ai_scored", "teacher_reviewed"]))
    pool = list(db.scalars(stmt.order_by(GradeTask.id.desc()).limit(200)))
    # 低置信度优先
    low = [t for t in pool if (t.ai_confidence or 0) <= body.max_confidence]
    high = [t for t in pool if t not in low]
    random.shuffle(low)
    random.shuffle(high)
    picked = (low + high)[: body.n]
    if not picked:
        return []
    for t in picked:
        t.qc_status = "sampled"
    write_audit(db, user=admin, action="grade.qc_sample", resource=f"n={len(picked)}")
    db.commit()
    return [_out(t, db.get(Question, t.question_id), db.get(User, t.user_id)) for t in picked]


@router.post("/{tid}/qc", response_model=GradeOut)
def mark_qc(
    tid: int,
    body: QcIn,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> GradeOut:
    t = db.get(GradeTask, tid)
    if not t:
        raise HTTPException(status_code=404, detail="任务不存在")
    t.qc_status = body.result
    t.qc_note = body.note.strip()
    t.qc_by = admin.id
    t.qc_at = datetime.now(timezone.utc)
    write_audit(db, user=admin, action="grade.qc", resource=f"{tid}:{body.result}")
    db.commit()
    db.refresh(t)
    return _out(t, db.get(Question, t.question_id), db.get(User, t.user_id))


@router.post("/{tid}/ai-score", response_model=GradeOut)
async def run_ai_score(
    tid: int,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> GradeOut:
    t = db.get(GradeTask, tid)
    if not t:
        raise HTTPException(status_code=404, detail="任务不存在")
    q = db.get(Question, t.question_id)
    if not q:
        raise HTTPException(status_code=404, detail="题目不存在")
    t = await ai_grade_task(db, t, q, admin)
    write_audit(db, user=admin, action="grade.ai", resource=str(tid))
    from ..services.workflow_engine import dispatch_event

    dispatch_event(
        db,
        "grade.ai_done",
        {
            "task_id": tid,
            "user_id": t.user_id,
            "body": f"任务 #{tid} AI 初评完成，请尽快复核。",
        },
    )
    db.commit()
    return _out(t, q, db.get(User, t.user_id))


@router.post("/{tid}/review", response_model=GradeOut)
def teacher_review(
    tid: int,
    body: ReviewIn,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> GradeOut:
    t = db.get(GradeTask, tid)
    if not t:
        raise HTTPException(status_code=404, detail="任务不存在")
    q = db.get(Question, t.question_id)
    if body.teacher_score > t.max_score:
        raise HTTPException(status_code=400, detail=f"分数不能超过满分 {t.max_score}")
    t.teacher_score = body.teacher_score
    t.teacher_feedback = body.teacher_feedback.strip()
    t.status = "teacher_reviewed"
    t.reviewed_by = admin.id
    t.reviewed_at = datetime.now(timezone.utc)

    score, _ = final_score(t)
    if score is not None and score < t.max_score * 0.6 and q:
        exists = db.scalar(
            select(WrongItem).where(
                WrongItem.user_id == t.user_id,
                WrongItem.question_id == t.question_id,
                WrongItem.mastered.is_(False),
            )
        )
        if not exists:
            db.add(
                WrongItem(
                    user_id=t.user_id,
                    question_id=t.question_id,
                    paper_id=t.paper_id,
                    submission_id=t.submission_id,
                    user_answer=t.answer_text,
                    correct_answer=q.answer,
                    knowledge_points=q.knowledge_points,
                    source="subjective",
                )
            )

    db.add(
        Notification(
            user_id=t.user_id,
            title="主观题已复核",
            body=f"教师已复核你的作答，得分 {body.teacher_score}/{t.max_score}。",
            link="/practice",
            kind="grade",
        )
    )
    write_audit(db, user=admin, action="grade.review", resource=str(tid))
    from ..services.workflow_engine import dispatch_event

    dispatch_event(
        db,
        "grade.reviewed",
        {
            "task_id": tid,
            "user_id": t.user_id,
            "title": "主观题已复核",
            "body": f"教师已复核你的作答，得分 {body.teacher_score}/{t.max_score}。",
            "link": "/practice",
        },
    )
    db.commit()
    db.refresh(t)
    return _out(t, q, db.get(User, t.user_id))
