from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit_util import write_audit
from ..auth import get_current_user
from ..db import get_db
from ..models import Ebook, EbookChapter, EbookProgress, User
from ..rbac import require_staff

router = APIRouter(prefix="/ebooks", tags=["ebooks"])


class ChapterIn(BaseModel):
    title: str
    content: str = ""
    sort_order: int = 0


class ChapterOut(BaseModel):
    id: int
    title: str
    content: str
    sort_order: int

    model_config = {"from_attributes": True}


class EbookIn(BaseModel):
    title: str
    cover: str = ""
    summary: str = ""
    status: str = "draft"


class EbookOut(BaseModel):
    id: int
    title: str
    cover: str
    summary: str
    status: str
    chapters: List[ChapterOut] = Field(default_factory=list)
    created_at: Optional[str] = None


def _out(db: Session, e: Ebook) -> EbookOut:
    chs = list(
        db.scalars(
            select(EbookChapter).where(EbookChapter.ebook_id == e.id).order_by(EbookChapter.sort_order, EbookChapter.id)
        )
    )
    return EbookOut(
        id=e.id,
        title=e.title,
        cover=e.cover,
        summary=e.summary,
        status=e.status,
        chapters=[ChapterOut.model_validate(c) for c in chs],
        created_at=e.created_at.isoformat() if e.created_at else None,
    )


@router.get("", response_model=List[EbookOut])
def list_ebooks(published_only: bool = False, db: Session = Depends(get_db)) -> List[EbookOut]:
    stmt = select(Ebook).order_by(Ebook.id.desc())
    if published_only:
        stmt = stmt.where(Ebook.status == "published")
    return [_out(db, e) for e in db.scalars(stmt)]


@router.get("/{eid}", response_model=EbookOut)
def get_ebook(eid: int, db: Session = Depends(get_db)) -> EbookOut:
    e = db.get(Ebook, eid)
    if not e:
        raise HTTPException(status_code=404, detail="电子书不存在")
    return _out(db, e)


@router.post("", response_model=EbookOut)
def create_ebook(
    body: EbookIn,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> EbookOut:
    e = Ebook(**body.model_dump())
    db.add(e)
    write_audit(db, user=admin, action="ebook.create", resource=body.title)
    db.commit()
    db.refresh(e)
    return _out(db, e)


@router.patch("/{eid}", response_model=EbookOut)
def update_ebook(
    eid: int,
    body: EbookIn,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> EbookOut:
    e = db.get(Ebook, eid)
    if not e:
        raise HTTPException(status_code=404, detail="电子书不存在")
    for k, v in body.model_dump().items():
        setattr(e, k, v)
    write_audit(db, user=admin, action="ebook.update", resource=str(eid))
    db.commit()
    return _out(db, e)


@router.post("/{eid}/chapters", response_model=EbookOut)
def add_chapter(
    eid: int,
    body: ChapterIn,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> EbookOut:
    if not db.get(Ebook, eid):
        raise HTTPException(status_code=404, detail="电子书不存在")
    db.add(EbookChapter(ebook_id=eid, **body.model_dump()))
    write_audit(db, user=admin, action="ebook.chapter", resource=str(eid))
    db.commit()
    return _out(db, db.get(Ebook, eid))  # type: ignore[arg-type]


@router.delete("/{eid}")
def delete_ebook(
    eid: int,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> dict:
    e = db.get(Ebook, eid)
    if not e:
        raise HTTPException(status_code=404, detail="电子书不存在")
    db.delete(e)
    write_audit(db, user=admin, action="ebook.delete", resource=str(eid))
    db.commit()
    return {"status": "ok"}


class ProgressIn(BaseModel):
    chapter_id: Optional[int] = None
    percent: int = 0


@router.get("/{eid}/progress")
def get_progress(
    eid: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    row = db.scalar(
        select(EbookProgress).where(EbookProgress.user_id == user.id, EbookProgress.ebook_id == eid)
    )
    if not row:
        return {"ebook_id": eid, "chapter_id": None, "percent": 0}
    return {"ebook_id": eid, "chapter_id": row.chapter_id, "percent": row.percent}


@router.post("/{eid}/progress")
def upsert_progress(
    eid: int,
    body: ProgressIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if not db.get(Ebook, eid):
        raise HTTPException(status_code=404, detail="电子书不存在")
    row = db.scalar(
        select(EbookProgress).where(EbookProgress.user_id == user.id, EbookProgress.ebook_id == eid)
    )
    percent = max(0, min(100, int(body.percent)))
    if not row:
        row = EbookProgress(
            user_id=user.id,
            ebook_id=eid,
            chapter_id=body.chapter_id,
            percent=percent,
        )
        db.add(row)
    else:
        row.chapter_id = body.chapter_id
        row.percent = max(row.percent, percent)
    db.commit()
    return {"ebook_id": eid, "chapter_id": row.chapter_id, "percent": row.percent}
