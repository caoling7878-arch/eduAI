from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Announcement, Course, LabPage, Paper
from ..routers.api_tokens import resolve_api_token, token_has_scope

router = APIRouter(prefix="/public/v1", tags=["public-api"])


def require_api_key(
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(default=None),
    authorization: Optional[str] = Header(default=None),
):
    raw = x_api_key
    if not raw and authorization and authorization.lower().startswith("bearer "):
        raw = authorization.split(" ", 1)[1].strip()
    token = resolve_api_token(db, raw or "")
    if not token:
        raise HTTPException(status_code=401, detail="无效或缺失 API Token（X-API-Key / Bearer）")
    return token


@router.get("/courses")
def public_courses(token=Depends(require_api_key), db: Session = Depends(get_db)):
    if not token_has_scope(token, "courses:read"):
        raise HTTPException(status_code=403, detail="缺少 courses:read 权限")
    rows = list(db.scalars(select(Course).where(Course.status == "published").order_by(Course.sort_order)))
    return [
        {
            "id": c.id,
            "title": c.title,
            "summary": c.summary,
            "price_type": c.price_type,
            "price": c.price,
            "student_count": c.student_count,
        }
        for c in rows
    ]


@router.get("/papers")
def public_papers(token=Depends(require_api_key), db: Session = Depends(get_db)):
    if not token_has_scope(token, "papers:read"):
        raise HTTPException(status_code=403, detail="缺少 papers:read 权限")
    rows = list(db.scalars(select(Paper).where(Paper.status == "published")))
    out = []
    for p in rows:
        try:
            qids = json.loads(p.question_ids or "[]")
        except json.JSONDecodeError:
            qids = []
        out.append({"id": p.id, "title": p.title, "question_count": len(qids)})
    return out


@router.get("/announcements")
def public_announcements(token=Depends(require_api_key), db: Session = Depends(get_db)):
    if not token_has_scope(token, "announcements:read"):
        raise HTTPException(status_code=403, detail="缺少 announcements:read 权限")
    rows = list(
        db.scalars(
            select(Announcement).where(Announcement.published.is_(True)).order_by(Announcement.id.desc()).limit(20)
        )
    )
    return [{"id": a.id, "title": a.title, "body": a.body, "views": a.views} for a in rows]


@router.get("/labs")
def public_labs(token=Depends(require_api_key), db: Session = Depends(get_db)):
    if not token_has_scope(token, "labs:read"):
        raise HTTPException(status_code=403, detail="缺少 labs:read 权限")
    rows = list(db.scalars(select(LabPage).order_by(LabPage.id)))
    return [
        {
            "page_key": p.page_key,
            "title": p.title,
            "category": p.category,
            "preview_path": p.preview_path,
        }
        for p in rows
    ]
