from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..db import get_db
from ..models import Notification, User
from ..rbac import require_staff

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotifOut(BaseModel):
    id: int
    title: str
    body: str
    link: str
    kind: str
    read: bool
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


class NotifIn(BaseModel):
    user_id: int
    title: str
    body: str = ""
    link: str = ""
    kind: str = "system"


def _out(n: Notification) -> NotifOut:
    return NotifOut(
        id=n.id,
        title=n.title,
        body=n.body,
        link=n.link,
        kind=n.kind,
        read=n.read,
        created_at=n.created_at.isoformat() if n.created_at else None,
    )


@router.get("/me", response_model=List[NotifOut])
def my_notifications(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[NotifOut]:
    rows = list(
        db.scalars(
            select(Notification).where(Notification.user_id == user.id).order_by(Notification.id.desc()).limit(50)
        )
    )
    return [_out(n) for n in rows]


@router.get("/me/unread-count")
def unread_count(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    n = db.scalar(
        select(func.count()).select_from(Notification).where(
            Notification.user_id == user.id,
            Notification.read.is_(False),
        )
    )
    return {"count": int(n or 0)}


@router.post("/me/{nid}/read")
def mark_read(
    nid: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    n = db.get(Notification, nid)
    if not n or n.user_id != user.id:
        raise HTTPException(status_code=404, detail="消息不存在")
    n.read = True
    db.commit()
    return {"status": "ok"}


@router.post("/me/read-all")
def mark_all_read(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    for n in db.scalars(select(Notification).where(Notification.user_id == user.id, Notification.read.is_(False))):
        n.read = True
    db.commit()
    return {"status": "ok"}


@router.post("", response_model=NotifOut)
def create_notification(
    body: NotifIn,
    _: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> NotifOut:
    n = Notification(**body.model_dump())
    db.add(n)
    db.commit()
    db.refresh(n)
    return _out(n)
