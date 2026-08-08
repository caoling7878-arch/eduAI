from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit_util import write_audit
from ..db import get_db
from ..models import DailyArticle, User
from ..rbac import require_staff

router = APIRouter(prefix="/articles", tags=["articles"])


class ArticleIn(BaseModel):
    title: str
    summary: str = ""
    body: str = ""
    lang: str = "zh"
    published: bool = True
    day_tag: str = ""


class ArticleOut(BaseModel):
    id: int
    title: str
    summary: str
    body: str
    lang: str
    published: bool
    day_tag: str
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


def _out(a: DailyArticle) -> ArticleOut:
    return ArticleOut(
        id=a.id,
        title=a.title,
        summary=a.summary,
        body=a.body,
        lang=a.lang,
        published=a.published,
        day_tag=a.day_tag,
        created_at=a.created_at.isoformat() if a.created_at else None,
    )


@router.get("", response_model=List[ArticleOut])
def list_articles(published_only: bool = True, db: Session = Depends(get_db)) -> List[ArticleOut]:
    stmt = select(DailyArticle).order_by(DailyArticle.id.desc())
    if published_only:
        stmt = stmt.where(DailyArticle.published.is_(True))
    return [_out(a) for a in db.scalars(stmt)]


@router.get("/{aid}", response_model=ArticleOut)
def get_article(aid: int, db: Session = Depends(get_db)) -> ArticleOut:
    a = db.get(DailyArticle, aid)
    if not a or (not a.published):
        raise HTTPException(status_code=404, detail="文章不存在")
    return _out(a)


@router.post("", response_model=ArticleOut)
def create_article(
    body: ArticleIn,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> ArticleOut:
    a = DailyArticle(**body.model_dump())
    db.add(a)
    write_audit(db, user=admin, action="article.create", resource=body.title)
    db.commit()
    db.refresh(a)
    return _out(a)


@router.patch("/{aid}", response_model=ArticleOut)
def update_article(
    aid: int,
    body: ArticleIn,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> ArticleOut:
    a = db.get(DailyArticle, aid)
    if not a:
        raise HTTPException(status_code=404, detail="文章不存在")
    for k, v in body.model_dump().items():
        setattr(a, k, v)
    write_audit(db, user=admin, action="article.update", resource=str(aid))
    db.commit()
    db.refresh(a)
    return _out(a)


@router.delete("/{aid}")
def delete_article(
    aid: int,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> dict:
    a = db.get(DailyArticle, aid)
    if not a:
        raise HTTPException(status_code=404, detail="文章不存在")
    db.delete(a)
    write_audit(db, user=admin, action="article.delete", resource=str(aid))
    db.commit()
    return {"status": "ok"}
