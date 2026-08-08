"""多租户用量包：配额校验与扣减。"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Tenant, TenantSubscription, UsagePack, User


def seed_billing(db: Session) -> dict:
    tenant = db.scalar(select(Tenant).where(Tenant.slug == "demo-school"))
    created_tenant = False
    if not tenant:
        tenant = Tenant(name="演示学校", slug="demo-school", status="active")
        db.add(tenant)
        db.flush()
        created_tenant = True

    packs = list(db.scalars(select(UsagePack)))
    created_packs = 0
    if not packs:
        defaults = [
            UsagePack(
                name="体验包",
                price=0,
                days=30,
                token_quota=100_000,
                request_quota=500,
                description="适合试用：约 10 万 Token / 500 次调用",
                enabled=True,
            ),
            UsagePack(
                name="标准校包",
                price=299,
                days=30,
                token_quota=2_000_000,
                request_quota=10_000,
                description="中小规模校区月度用量",
                enabled=True,
            ),
            UsagePack(
                name="旗舰校包",
                price=999,
                days=30,
                token_quota=10_000_000,
                request_quota=50_000,
                description="大体量校区 / 教培机构",
                enabled=True,
            ),
        ]
        for p in defaults:
            db.add(p)
        db.flush()
        packs = defaults
        created_packs = len(defaults)

    # 绑定无租户用户到演示学校
    for u in db.scalars(select(User).where(User.tenant_id.is_(None))):
        u.tenant_id = tenant.id

    sub = db.scalar(
        select(TenantSubscription).where(
            TenantSubscription.tenant_id == tenant.id,
            TenantSubscription.status == "active",
        )
    )
    created_sub = False
    if not sub:
        pack = packs[0]
        today = date.today()
        sub = TenantSubscription(
            tenant_id=tenant.id,
            pack_id=pack.id,
            status="active",
            tokens_used=0,
            requests_used=0,
            token_quota=pack.token_quota,
            request_quota=pack.request_quota,
            starts_at=today.isoformat(),
            ends_at=(today + timedelta(days=pack.days)).isoformat(),
        )
        db.add(sub)
        created_sub = True

    db.commit()
    return {
        "tenant_id": tenant.id,
        "created_tenant": created_tenant,
        "created_packs": created_packs,
        "created_sub": created_sub,
    }


def active_subscription(db: Session, tenant_id: int) -> Optional[TenantSubscription]:
    sub = db.scalar(
        select(TenantSubscription)
        .where(
            TenantSubscription.tenant_id == tenant_id,
            TenantSubscription.status == "active",
        )
        .order_by(TenantSubscription.id.desc())
    )
    if not sub:
        return None
    today = date.today().isoformat()
    if sub.ends_at and sub.ends_at < today:
        sub.status = "expired"
        db.commit()
        return None
    return sub


def resolve_tenant_id(db: Session, user: Optional[User]) -> Optional[int]:
    if user and getattr(user, "tenant_id", None):
        return int(user.tenant_id)
    t = db.scalar(select(Tenant).where(Tenant.slug == "demo-school"))
    return t.id if t else None


def check_quota(db: Session, user: Optional[User]) -> Tuple[bool, str, Optional[TenantSubscription]]:
    """返回 (ok, message, subscription)。无租户时放行。"""
    tid = resolve_tenant_id(db, user)
    if not tid:
        return True, "无租户限制", None
    tenant = db.get(Tenant, tid)
    if tenant and tenant.status == "suspended":
        return False, "租户已停用，请联系管理员", None
    sub = active_subscription(db, tid)
    if not sub:
        return False, "当前无有效用量包，请为租户开通套餐", None
    if sub.requests_used >= sub.request_quota:
        return False, f"本月调用次数已用尽（{sub.requests_used}/{sub.request_quota}）", sub
    if sub.tokens_used >= sub.token_quota:
        return False, f"本月 Token 已用尽（{sub.tokens_used}/{sub.token_quota}）", sub
    return True, "ok", sub


def consume_quota(
    db: Session,
    user: Optional[User],
    *,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    requests: int = 1,
) -> None:
    tid = resolve_tenant_id(db, user)
    if not tid:
        return
    sub = active_subscription(db, tid)
    if not sub:
        return
    sub.requests_used = int(sub.requests_used or 0) + max(0, requests)
    sub.tokens_used = int(sub.tokens_used or 0) + max(0, int(prompt_tokens) + int(completion_tokens))


def assign_pack(db: Session, tenant_id: int, pack_id: int) -> TenantSubscription:
    pack = db.get(UsagePack, pack_id)
    if not pack:
        raise ValueError("用量包不存在")
    # 结束旧订阅
    for old in db.scalars(
        select(TenantSubscription).where(
            TenantSubscription.tenant_id == tenant_id,
            TenantSubscription.status == "active",
        )
    ):
        old.status = "cancelled"
    today = date.today()
    sub = TenantSubscription(
        tenant_id=tenant_id,
        pack_id=pack.id,
        status="active",
        tokens_used=0,
        requests_used=0,
        token_quota=pack.token_quota,
        request_quota=pack.request_quota,
        starts_at=today.isoformat(),
        ends_at=(today + timedelta(days=pack.days)).isoformat(),
    )
    db.add(sub)
    db.flush()
    return sub
