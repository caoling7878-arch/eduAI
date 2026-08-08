"""租户与用量包管理 API。"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit_util import write_audit
from ..auth import get_current_user
from ..db import get_db
from ..models import Tenant, UsagePack, User
from ..rbac import require_admin, require_staff
from ..services.billing import (
    active_subscription,
    assign_pack,
    resolve_tenant_id,
    seed_billing,
)

router = APIRouter(prefix="/billing", tags=["billing"])


class TenantIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(min_length=1, max_length=64)
    status: str = "active"


class PackIn(BaseModel):
    name: str
    price: float = 0
    days: int = 30
    token_quota: int = 200000
    request_quota: int = 2000
    description: str = ""
    enabled: bool = True


class AssignIn(BaseModel):
    tenant_id: int
    pack_id: int


class AssignUserIn(BaseModel):
    user_id: int
    tenant_id: int


@router.post("/seed")
def seed(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    return seed_billing(db)


@router.get("/tenants")
def list_tenants(_: User = Depends(require_staff), db: Session = Depends(get_db)) -> list:
    seed_billing(db)
    out = []
    for t in db.scalars(select(Tenant).order_by(Tenant.id)):
        sub = active_subscription(db, t.id)
        pack = db.get(UsagePack, sub.pack_id) if sub else None
        out.append(
            {
                "id": t.id,
                "name": t.name,
                "slug": t.slug,
                "status": t.status,
                "subscription": None
                if not sub
                else {
                    "id": sub.id,
                    "pack_id": sub.pack_id,
                    "pack_name": pack.name if pack else "",
                    "tokens_used": sub.tokens_used,
                    "token_quota": sub.token_quota,
                    "requests_used": sub.requests_used,
                    "request_quota": sub.request_quota,
                    "starts_at": sub.starts_at,
                    "ends_at": sub.ends_at,
                    "token_pct": round(100 * sub.tokens_used / max(sub.token_quota, 1), 1),
                    "request_pct": round(100 * sub.requests_used / max(sub.request_quota, 1), 1),
                },
            }
        )
    return out


@router.post("/tenants")
def create_tenant(
    body: TenantIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    if db.scalar(select(Tenant).where(Tenant.slug == body.slug.strip())):
        raise HTTPException(status_code=409, detail="slug 已存在")
    t = Tenant(name=body.name.strip(), slug=body.slug.strip(), status=body.status)
    db.add(t)
    write_audit(db, user=admin, action="tenant.create", resource=body.slug)
    db.commit()
    db.refresh(t)
    return {"id": t.id, "name": t.name, "slug": t.slug, "status": t.status}


@router.get("/packs")
def list_packs(_: User = Depends(require_staff), db: Session = Depends(get_db)) -> list:
    seed_billing(db)
    return [
        {
            "id": p.id,
            "name": p.name,
            "price": p.price,
            "days": p.days,
            "token_quota": p.token_quota,
            "request_quota": p.request_quota,
            "description": p.description,
            "enabled": p.enabled,
        }
        for p in db.scalars(select(UsagePack).order_by(UsagePack.price))
    ]


@router.post("/packs")
def create_pack(
    body: PackIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    p = UsagePack(
        name=body.name,
        price=body.price,
        days=body.days,
        token_quota=body.token_quota,
        request_quota=body.request_quota,
        description=body.description,
        enabled=body.enabled,
    )
    db.add(p)
    write_audit(db, user=admin, action="usage_pack.create", resource=body.name)
    db.commit()
    db.refresh(p)
    return {"id": p.id, "name": p.name}


@router.post("/assign")
def assign(
    body: AssignIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    if not db.get(Tenant, body.tenant_id):
        raise HTTPException(status_code=404, detail="租户不存在")
    try:
        sub = assign_pack(db, body.tenant_id, body.pack_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    write_audit(
        db,
        user=admin,
        action="tenant.assign_pack",
        resource=f"{body.tenant_id}:{body.pack_id}",
    )
    db.commit()
    return {
        "subscription_id": sub.id,
        "ends_at": sub.ends_at,
        "token_quota": sub.token_quota,
        "request_quota": sub.request_quota,
    }


@router.post("/assign-user")
def assign_user(
    body: AssignUserIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    u = db.get(User, body.user_id)
    t = db.get(Tenant, body.tenant_id)
    if not u or not t:
        raise HTTPException(status_code=404, detail="用户或租户不存在")
    u.tenant_id = t.id
    write_audit(db, user=admin, action="user.assign_tenant", resource=f"{u.id}:{t.id}")
    db.commit()
    return {"user_id": u.id, "tenant_id": t.id}


@router.get("/me")
def my_usage(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    seed_billing(db)
    tid = resolve_tenant_id(db, user)
    if not tid:
        return {"tenant": None, "subscription": None}
    t = db.get(Tenant, tid)
    sub = active_subscription(db, tid)
    pack = db.get(UsagePack, sub.pack_id) if sub else None
    return {
        "tenant": {"id": t.id, "name": t.name, "slug": t.slug, "status": t.status} if t else None,
        "subscription": None
        if not sub
        else {
            "pack_name": pack.name if pack else "",
            "tokens_used": sub.tokens_used,
            "token_quota": sub.token_quota,
            "requests_used": sub.requests_used,
            "request_quota": sub.request_quota,
            "ends_at": sub.ends_at,
            "token_pct": round(100 * sub.tokens_used / max(sub.token_quota, 1), 1),
            "request_pct": round(100 * sub.requests_used / max(sub.request_quota, 1), 1),
        },
    }
