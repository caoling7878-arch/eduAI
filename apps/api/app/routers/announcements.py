from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit_util import write_audit
from ..db import get_db
from ..models import Announcement, User
from ..rbac import require_staff
from ..schemas import AnnouncementIn, AnnouncementOut

router = APIRouter(prefix="/announcements", tags=["announcements"])


@router.get("", response_model=list[AnnouncementOut])
def list_announcements(
    published_only: bool = False,
    db: Session = Depends(get_db),
) -> list[Announcement]:
    stmt = select(Announcement).order_by(Announcement.id.desc())
    if published_only:
        stmt = stmt.where(Announcement.published.is_(True))
    return list(db.scalars(stmt))


@router.get("/{aid}", response_model=AnnouncementOut)
def get_announcement(aid: int, db: Session = Depends(get_db)) -> Announcement:
    a = db.get(Announcement, aid)
    if not a:
        raise HTTPException(status_code=404, detail="公告不存在")
    a.views += 1
    db.commit()
    db.refresh(a)
    return a


@router.post("", response_model=AnnouncementOut)
def create_announcement(
    body: AnnouncementIn,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> Announcement:
    a = Announcement(**body.model_dump())
    db.add(a)
    write_audit(db, user=admin, action="announcement.create", resource=body.title)
    db.commit()
    db.refresh(a)
    return a


@router.patch("/{aid}", response_model=AnnouncementOut)
def update_announcement(
    aid: int,
    body: AnnouncementIn,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> Announcement:
    a = db.get(Announcement, aid)
    if not a:
        raise HTTPException(status_code=404, detail="公告不存在")
    for k, v in body.model_dump().items():
        setattr(a, k, v)
    write_audit(db, user=admin, action="announcement.update", resource=str(aid))
    db.commit()
    db.refresh(a)
    return a


@router.delete("/{aid}")
def delete_announcement(
    aid: int,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    a = db.get(Announcement, aid)
    if not a:
        raise HTTPException(status_code=404, detail="公告不存在")
    db.delete(a)
    write_audit(db, user=admin, action="announcement.delete", resource=str(aid))
    db.commit()
    return {"status": "ok"}
