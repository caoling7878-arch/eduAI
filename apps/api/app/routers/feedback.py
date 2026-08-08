from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import get_current_user, get_optional_user
from ..db import get_db
from ..models import FeedbackTicket, Notification, User
from ..rbac import require_staff

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackIn(BaseModel):
    category: str = "general"
    title: str = Field(min_length=1, max_length=200)
    body: str = ""


class ReplyIn(BaseModel):
    reply: str
    status: str = "done"


class FeedbackOut(BaseModel):
    id: int
    user_id: Optional[int]
    user_name: str = ""
    category: str
    title: str
    body: str
    status: str
    reply: str
    created_at: Optional[str] = None


def _out(t: FeedbackTicket, db: Optional[Session] = None) -> FeedbackOut:
    name = ""
    if t.user_id and db is not None:
        u = db.get(User, t.user_id)
        name = u.display_name if u else ""
    return FeedbackOut(
        id=t.id,
        user_id=t.user_id,
        user_name=name,
        category=t.category,
        title=t.title,
        body=t.body,
        status=t.status,
        reply=t.reply,
        created_at=t.created_at.isoformat() if t.created_at else None,
    )


@router.post("", response_model=FeedbackOut)
def create_feedback(
    body: FeedbackIn,
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> FeedbackOut:
    t = FeedbackTicket(
        user_id=user.id if user else None,
        category=body.category,
        title=body.title,
        body=body.body,
        status="open",
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    from ..services.workflow_engine import dispatch_event

    dispatch_event(
        db,
        "feedback.created",
        {
            "ticket_id": t.id,
            "user_id": t.user_id,
            "body": f"「{t.title}」已提交，请及时处理。",
        },
    )
    db.commit()
    return _out(t, db)


@router.get("/me", response_model=List[FeedbackOut])
def my_feedback(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> List[FeedbackOut]:
    rows = list(
        db.scalars(
            select(FeedbackTicket).where(FeedbackTicket.user_id == user.id).order_by(FeedbackTicket.id.desc())
        )
    )
    return [_out(t, db) for t in rows]


@router.get("", response_model=List[FeedbackOut])
def admin_list(
    status: str = "",
    _: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> List[FeedbackOut]:
    stmt = select(FeedbackTicket).order_by(FeedbackTicket.id.desc()).limit(100)
    if status:
        stmt = stmt.where(FeedbackTicket.status == status)
    return [_out(t, db) for t in db.scalars(stmt)]


@router.post("/{tid}/reply", response_model=FeedbackOut)
def reply_ticket(
    tid: int,
    body: ReplyIn,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> FeedbackOut:
    t = db.get(FeedbackTicket, tid)
    if not t:
        raise HTTPException(status_code=404, detail="工单不存在")
    t.reply = body.reply
    t.status = body.status
    if t.user_id:
        db.add(
            Notification(
                user_id=t.user_id,
                title="反馈已回复",
                body=body.reply[:120],
                link="/feedback",
                kind="system",
            )
        )
    db.commit()
    db.refresh(t)
    return _out(t, db)
