"""学员隐私合规：数据导出与账号注销。"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..audit_util import write_audit
from ..auth import get_current_user, verify_password
from ..db import get_db
from ..models import (
    Checkin,
    FeedbackTicket,
    MathCalcDaily,
    Notification,
    Order,
    ProgressItem,
    Question,
    StudyPlan,
    Submission,
    User,
    VocabDailyLog,
    VocabProgress,
    VocabReward,
    WrongItem,
)

router = APIRouter(prefix="/privacy", tags=["privacy"])

PROTECTED_EMAILS = {"admin@edu.ai", "teacher@edu.ai", "student@edu.ai"}


class DeleteIn(BaseModel):
    password: str = Field(min_length=1)
    confirm: str = Field(description="须填写 DELETE")


@router.get("/export")
def export_my_data(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    wrongs = []
    for w in db.scalars(select(WrongItem).where(WrongItem.user_id == user.id)):
        q = db.get(Question, w.question_id)
        wrongs.append(
            {
                "id": w.id,
                "stem": q.stem if q else "",
                "user_answer": w.user_answer,
                "correct_answer": w.correct_answer,
                "knowledge_points": w.knowledge_points,
                "mastered": w.mastered,
                "source": w.source,
            }
        )

    vocab_rows = list(db.scalars(select(VocabProgress).where(VocabProgress.user_id == user.id)))
    payload = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "profile": {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "role": user.role,
            "status": user.status,
            "tags": user.tags,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        "progress": [
            {
                "course_id": p.course_id,
                "item_id": p.item_id,
                "status": p.status,
                "score": p.score,
                "meta_json": p.meta_json,
            }
            for p in db.scalars(select(ProgressItem).where(ProgressItem.user_id == user.id))
        ],
        "checkins": [
            {
                "day": c.day,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in db.scalars(select(Checkin).where(Checkin.user_id == user.id))
        ],
        "study_plans": [
            {
                "title": p.title,
                "done": p.done,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in db.scalars(select(StudyPlan).where(StudyPlan.user_id == user.id))
        ],
        "orders": [
            {
                "id": o.id,
                "amount": o.amount,
                "status": o.status,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in db.scalars(select(Order).where(Order.user_id == user.id))
        ],
        "wrongbook": wrongs,
        "submissions": [
            {
                "id": s.id,
                "paper_id": s.paper_id,
                "score": s.score,
                "total": s.total,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in db.scalars(select(Submission).where(Submission.user_id == user.id))
        ],
        "notifications": [
            {"title": n.title, "body": n.body, "read": n.read, "kind": n.kind}
            for n in db.scalars(
                select(Notification).where(Notification.user_id == user.id).limit(200)
            )
        ],
        "vocab_progress_count": len(vocab_rows),
        "vocab_daily_logs": [
            {
                "day": v.day,
                "bank": v.bank,
                "completed": v.completed,
                "stars_earned": v.stars_earned,
            }
            for v in db.scalars(select(VocabDailyLog).where(VocabDailyLog.user_id == user.id))
        ],
        "math_calc_dailies": [
            {
                "day": d.day,
                "grade": d.grade,
                "topic": d.topic,
                "correct_count": d.correct_count,
                "total_count": d.total_count,
                "elapsed_seconds": getattr(d, "elapsed_seconds", 0),
                "submitted": d.submitted,
            }
            for d in db.scalars(select(MathCalcDaily).where(MathCalcDaily.user_id == user.id))
        ],
        "feedback": [
            {"id": f.id, "title": f.title, "status": f.status, "category": f.category}
            for f in db.scalars(select(FeedbackTicket).where(FeedbackTicket.user_id == user.id))
        ],
    }
    raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    write_audit(db, user=user, action="privacy.export", resource=f"user:{user.id}")
    db.commit()
    return StreamingResponse(
        iter([raw]),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="eduai-data-{user.id}.json"'},
    )


@router.post("/delete-account")
def delete_account(
    body: DeleteIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if body.confirm.strip().upper() != "DELETE":
        raise HTTPException(status_code=400, detail="请在 confirm 中填写 DELETE 以确认注销")
    if user.email.lower() in PROTECTED_EMAILS:
        raise HTTPException(status_code=400, detail="演示种子账号不可注销，请使用自行注册的账号")
    if user.role == "admin":
        raise HTTPException(status_code=400, detail="管理员账号请联系运维处理，不可自助注销")
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=400, detail="密码不正确")

    uid = user.id
    email = user.email
    for model in (
        ProgressItem,
        Checkin,
        StudyPlan,
        WrongItem,
        Notification,
        Submission,
        Order,
        VocabProgress,
        VocabDailyLog,
        VocabReward,
        MathCalcDaily,
        FeedbackTicket,
    ):
        db.execute(delete(model).where(model.user_id == uid))  # type: ignore[attr-defined]

    write_audit(db, user=user, action="privacy.delete_account", resource=email)
    db.delete(user)
    db.commit()
    return {"status": "ok", "message": "账号已注销，相关学习数据已删除"}
