from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit_util import write_audit
from ..db import get_db
from ..models import ApiToken, User
from ..rbac import require_admin

router = APIRouter(prefix="/api-tokens", tags=["api-tokens"])


class TokenIn(BaseModel):
    name: str
    scopes: str = Field(
        default="courses:read,announcements:read,labs:read,papers:read",
        description="逗号分隔权限",
    )


class TokenOut(BaseModel):
    id: int
    name: str
    token_prefix: str
    scopes: str
    enabled: bool
    last_used_at: Optional[str] = None
    created_at: Optional[str] = None
    # 仅创建时返回一次明文
    token: Optional[str] = None


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _out(row: ApiToken, token: Optional[str] = None) -> TokenOut:
    return TokenOut(
        id=row.id,
        name=row.name,
        token_prefix=row.token_prefix,
        scopes=row.scopes,
        enabled=row.enabled,
        last_used_at=row.last_used_at.isoformat() if row.last_used_at else None,
        created_at=row.created_at.isoformat() if row.created_at else None,
        token=token,
    )


@router.get("", response_model=List[TokenOut])
def list_tokens(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> List[TokenOut]:
    return [_out(t) for t in db.scalars(select(ApiToken).order_by(ApiToken.id.desc()))]


@router.post("", response_model=TokenOut)
def create_token(
    body: TokenIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> TokenOut:
    raw = "eduai_" + secrets.token_urlsafe(32)
    row = ApiToken(
        name=body.name.strip(),
        token_prefix=raw[:12],
        token_hash=hash_token(raw),
        scopes=body.scopes,
        enabled=True,
        created_by=admin.id,
    )
    db.add(row)
    write_audit(db, user=admin, action="api_token.create", resource=body.name)
    db.commit()
    db.refresh(row)
    return _out(row, token=raw)


@router.post("/{tid}/revoke")
def revoke_token(
    tid: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    row = db.get(ApiToken, tid)
    if not row:
        raise HTTPException(status_code=404, detail="Token 不存在")
    row.enabled = False
    write_audit(db, user=admin, action="api_token.revoke", resource=str(tid))
    db.commit()
    return {"status": "ok"}


def resolve_api_token(db: Session, raw: str) -> Optional[ApiToken]:
    if not raw or not raw.startswith("eduai_"):
        return None
    row = db.scalar(select(ApiToken).where(ApiToken.token_hash == hash_token(raw), ApiToken.enabled.is_(True)))
    if row:
        row.last_used_at = datetime.now(timezone.utc)
        db.commit()
    return row


def token_has_scope(token: ApiToken, scope: str) -> bool:
    scopes = {s.strip() for s in (token.scopes or "").split(",") if s.strip()}
    return "*" in scopes or scope in scopes
