from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..db import get_db
from ..models import Checkin, User
from ..schemas import CheckinOut

router = APIRouter(prefix="/checkins", tags=["checkins"])


def _streak(days: set[str], today: date) -> int:
    n = 0
    d = today
    while d.isoformat() in days:
        n += 1
        d -= timedelta(days=1)
    return n


@router.get("/me", response_model=CheckinOut)
def my_checkin(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CheckinOut:
    rows = list(db.scalars(select(Checkin.day).where(Checkin.user_id == user.id)))
    days = set(rows)
    today = date.today()
    return CheckinOut(
        day=today.isoformat(),
        streak=_streak(days, today),
        total=len(days),
        checked_today=today.isoformat() in days,
    )


@router.post("/me", response_model=CheckinOut)
def do_checkin(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CheckinOut:
    today = date.today().isoformat()
    exists = db.scalar(select(Checkin).where(Checkin.user_id == user.id, Checkin.day == today))
    if not exists:
        db.add(Checkin(user_id=user.id, day=today))
        db.commit()
    return my_checkin(user, db)


@router.get("/today-count")
def today_count(db: Session = Depends(get_db)) -> dict[str, int]:
    today = date.today().isoformat()
    n = db.scalar(select(func.count()).select_from(Checkin).where(Checkin.day == today)) or 0
    return {"count": int(n)}
