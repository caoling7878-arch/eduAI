from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit_util import write_audit
from ..auth import get_current_user
from ..db import SessionLocal, get_db
from ..models import GradeTask, Notification, Paper, Question, Submission, User, WrongItem
from ..rbac import require_staff
from ..schemas import PaperIn, PaperOut, SubmissionOut, SubmitIn
from ..services.grading import ai_grade_task

router = APIRouter(prefix="/papers", tags=["papers"])

SUBJECTIVE_TYPES = {"essay", "subjective"}


def _norm_objective_answer(raw: str, qtype: str) -> str:
    """多选题答案归一化为排序后的索引串，避免 2,0 与 0,2 判错。"""
    a = (raw or "").strip().replace("，", ",")
    if qtype == "multi":
        parts = [p.strip() for p in a.split(",") if p.strip()]
        try:
            parts.sort(key=lambda x: int(x))
        except ValueError:
            parts.sort()
        return ",".join(parts)
    return a


def _out(p: Paper) -> PaperOut:
    try:
        ids = json.loads(p.question_ids or "[]")
    except json.JSONDecodeError:
        ids = []
    return PaperOut(
        id=p.id,
        title=p.title,
        status=p.status,
        question_ids=ids if isinstance(ids, list) else [],
        created_at=p.created_at,
    )


@router.get("", response_model=list[PaperOut])
def list_papers(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[PaperOut]:
    return [_out(p) for p in db.scalars(select(Paper).order_by(Paper.id.desc()))]


@router.get("/{pid}/quiz")
def get_quiz(
    pid: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    p = db.get(Paper, pid)
    if not p or p.status != "published":
        raise HTTPException(status_code=404, detail="试卷不可用")
    try:
        qids = json.loads(p.question_ids or "[]")
    except json.JSONDecodeError:
        qids = []
    items = []
    for qid in qids:
        q = db.get(Question, int(qid))
        if not q:
            continue
        try:
            options = json.loads(q.options_json or "[]")
        except json.JSONDecodeError:
            options = []
        items.append(
            {
                "id": q.id,
                "type": q.type,
                "stem": q.stem,
                "options": options if isinstance(options, list) else [],
                "difficulty": q.difficulty,
                "knowledge_points": q.knowledge_points,
            }
        )
    return {"paper": _out(p), "questions": items}


@router.post("", response_model=PaperOut)
def create_paper(
    body: PaperIn,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> PaperOut:
    p = Paper(
        title=body.title,
        status=body.status,
        question_ids=json.dumps(body.question_ids),
    )
    db.add(p)
    write_audit(db, user=admin, action="paper.create", resource=body.title)
    db.commit()
    db.refresh(p)
    return _out(p)


@router.patch("/{pid}", response_model=PaperOut)
def update_paper(
    pid: int,
    body: PaperIn,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> PaperOut:
    p = db.get(Paper, pid)
    if not p:
        raise HTTPException(status_code=404, detail="试卷不存在")
    p.title = body.title
    p.status = body.status
    p.question_ids = json.dumps(body.question_ids)
    write_audit(db, user=admin, action="paper.update", resource=str(pid))
    db.commit()
    db.refresh(p)
    return _out(p)


async def _grade_background(task_ids: list[int], user_id: int) -> None:
    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        for tid in task_ids:
            t = db.get(GradeTask, tid)
            q = db.get(Question, t.question_id) if t else None
            if t and q and t.status == "pending":
                await ai_grade_task(db, t, q, user)
                db.add(
                    Notification(
                        user_id=t.user_id,
                        title="主观题 AI 初评完成",
                        body=f"得分 {t.ai_score}/{t.max_score}，等待教师复核。",
                        link="/practice",
                        kind="grade",
                    )
                )
                db.commit()
    finally:
        db.close()


@router.post("/submit", response_model=SubmissionOut)
async def submit_paper(
    body: SubmitIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SubmissionOut:
    p = db.get(Paper, body.paper_id)
    if not p or p.status != "published":
        raise HTTPException(status_code=404, detail="试卷不可用")
    try:
        qids = json.loads(p.question_ids or "[]")
    except json.JSONDecodeError:
        qids = []

    score = 0.0
    objective_total = 0.0
    grade_task_ids: list[int] = []

    for qid in qids:
        q = db.get(Question, int(qid))
        if not q:
            continue
        ans = _norm_objective_answer(body.answers.get(str(qid), ""), q.type)
        if q.type in SUBJECTIVE_TYPES:
            task = GradeTask(
                paper_id=p.id,
                question_id=q.id,
                user_id=user.id,
                answer_text=body.answers.get(str(qid), "").strip(),
                max_score=10,
                status="pending",
            )
            db.add(task)
            db.flush()
            grade_task_ids.append(task.id)
            continue

        objective_total += 1
        correct = _norm_objective_answer(q.answer or "", q.type)
        if ans == correct:
            score += 1
        else:
            db.add(
                WrongItem(
                    user_id=user.id,
                    question_id=q.id,
                    paper_id=p.id,
                    user_answer=ans,
                    correct_answer=q.answer,
                    knowledge_points=q.knowledge_points,
                    source="objective",
                    mastered=False,
                )
            )

    sub = Submission(
        paper_id=p.id,
        user_id=user.id,
        answers_json=json.dumps(body.answers, ensure_ascii=False),
        score=score,
        total=objective_total,
    )
    db.add(sub)
    db.flush()
    for tid in grade_task_ids:
        t = db.get(GradeTask, tid)
        if t:
            t.submission_id = sub.id

    if grade_task_ids:
        db.add(
            Notification(
                user_id=user.id,
                title="主观题已提交",
                body=f"共 {len(grade_task_ids)} 道主观题进入 AI 初评队列。",
                link="/messages",
                kind="grade",
            )
        )

    db.commit()
    db.refresh(sub)

    if grade_task_ids:
        asyncio.create_task(_grade_background(grade_task_ids, user.id))

    return SubmissionOut(
        id=sub.id,
        paper_id=sub.paper_id,
        score=sub.score,
        total=sub.total,
        answers=body.answers,
        created_at=sub.created_at,
    )
