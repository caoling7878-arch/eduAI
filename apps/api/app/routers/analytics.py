from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import (
    AuditLog,
    Checkin,
    ClassMember,
    ClassRoom,
    Course,
    FeedbackTicket,
    GradeTask,
    Order,
    ProgressItem,
    Question,
    Submission,
    Tenant,
    TenantSubscription,
    User,
    VocabProgress,
    WrongItem,
)
from ..rbac import require_admin, require_staff
from ..schemas import AuditOut, DashboardOut

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _day_range(days: int = 30) -> list[str]:
    today = date.today()
    return [(today - timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]


def _dt_day(value: Optional[datetime]) -> Optional[str]:
    if not value:
        return None
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value.date().isoformat()


class StudentOpsOut(BaseModel):
    id: int
    email: str
    display_name: str
    status: str
    tags: str
    created_at: Optional[str] = None
    checkins: int = 0
    submissions: int = 0
    wrong_open: int = 0
    progress_done: int = 0
    orders: int = 0
    paid_amount: float = 0
    member_plan: str = ""
    is_member: bool = False
    last_active: Optional[str] = None
    activity_score: int = 0


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(_: User = Depends(require_staff), db: Session = Depends(get_db)) -> DashboardOut:
    today = date.today().isoformat()
    days = _day_range(30)

    users = int(db.scalar(select(func.count()).select_from(User)) or 0)
    teachers = int(db.scalar(select(func.count()).select_from(User).where(User.role == "teacher")) or 0)
    students = int(db.scalar(select(func.count()).select_from(User).where(User.role == "student")) or 0)
    courses = int(db.scalar(select(func.count()).select_from(Course)) or 0)
    classes = int(db.scalar(select(func.count()).select_from(ClassRoom)) or 0)
    questions = int(db.scalar(select(func.count()).select_from(Question)) or 0)
    orders_n = int(db.scalar(select(func.count()).select_from(Order)) or 0)
    checkins_today = int(
        db.scalar(select(func.count()).select_from(Checkin).where(Checkin.day == today)) or 0
    )

    paid_orders = list(db.scalars(select(Order).where(Order.status == "paid")))
    member_uids = {o.user_id for o in paid_orders}
    revenue_total = round(sum(o.amount for o in paid_orders), 2)
    orders_today_rows = [o for o in paid_orders if _dt_day(o.created_at) == today]
    revenue_today = round(sum(o.amount for o in orders_today_rows), 2)
    orders_today = len(orders_today_rows)

    feedback_open = int(
        db.scalar(
            select(func.count())
            .select_from(FeedbackTicket)
            .where(FeedbackTicket.status.in_(["open", "processing"]))
        )
        or 0
    )
    grade_pending = int(
        db.scalar(
            select(func.count())
            .select_from(GradeTask)
            .where(GradeTask.status.in_(["pending", "ai_scored"]))
        )
        or 0
    )

    # 学习时长估算：完成进度 * 12 分钟 + 打卡 * 8 分钟（近 30 天）
    progress_done = int(
        db.scalar(
            select(func.count())
            .select_from(ProgressItem)
            .where(ProgressItem.status == "completed")
        )
        or 0
    )
    checkins_30 = int(db.scalar(select(func.count()).select_from(Checkin).where(Checkin.day.in_(days))) or 0)
    learning_minutes_30d = progress_done * 12 + checkins_30 * 8

    # 趋势
    checkin_counter: Counter = Counter(
        c.day for c in db.scalars(select(Checkin).where(Checkin.day.in_(days))).all()
    )
    user_counter: Counter = Counter()
    for u in db.scalars(select(User)).all():
        d = _dt_day(u.created_at)
        if d in days:
            user_counter[d] += 1
    order_counter: Counter = Counter()
    order_amount: dict[str, float] = defaultdict(float)
    for o in paid_orders:
        d = _dt_day(o.created_at)
        if d in days:
            order_counter[d] += 1
            order_amount[d] += o.amount

    # 活跃分布
    course_watch = int(
        db.scalar(select(func.count()).select_from(ProgressItem).where(ProgressItem.status != "")) or 0
    )
    submissions = int(db.scalar(select(func.count()).select_from(Submission)) or 0)
    vocab = int(db.scalar(select(func.count()).select_from(VocabProgress)) or 0)
    checkin_all = int(db.scalar(select(func.count()).select_from(Checkin)) or 0)

    # 学员活跃排行
    student_rows = list(db.scalars(select(User).where(User.role == "student")))
    checkin_by_user: Counter = Counter(
        c.user_id for c in db.scalars(select(Checkin)).all()
    )
    sub_by_user: Counter = Counter(
        s.user_id for s in db.scalars(select(Submission)).all()
    )
    prog_by_user: Counter = Counter(
        p.user_id
        for p in db.scalars(select(ProgressItem).where(ProgressItem.status == "completed")).all()
    )
    ranked = []
    for u in student_rows:
        score = checkin_by_user[u.id] * 3 + sub_by_user[u.id] * 5 + prog_by_user[u.id] * 2
        ranked.append(
            {
                "user_id": u.id,
                "display_name": u.display_name,
                "value": score,
                "label": f"打卡{checkin_by_user[u.id]} · 交卷{sub_by_user[u.id]}",
            }
        )
    ranked.sort(key=lambda x: x["value"], reverse=True)

    # 班级活跃
    class_ranks = []
    for c in db.scalars(select(ClassRoom)).all():
        mids = list(db.scalars(select(ClassMember.user_id).where(ClassMember.class_id == c.id)))
        act = sum(checkin_by_user[i] + sub_by_user[i] for i in mids)
        class_ranks.append(
            {
                "user_id": c.id,
                "display_name": c.name,
                "value": act,
                "label": f"{len(mids)} 人",
            }
        )
    class_ranks.sort(key=lambda x: x["value"], reverse=True)

    audits = list(db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(8)))

    # 租户用量摘要
    tenant_count = int(db.scalar(select(func.count()).select_from(Tenant)) or 0)
    token_used_total = token_quota_total = request_used_total = request_quota_total = 0
    token_pct_max = 0.0
    quota_alert_count = 0
    quota_tenants: list[dict] = []
    today_s = date.today().isoformat()
    for t in db.scalars(select(Tenant).order_by(Tenant.id)):
        sub = db.scalar(
            select(TenantSubscription)
            .where(
                TenantSubscription.tenant_id == t.id,
                TenantSubscription.status == "active",
            )
            .order_by(TenantSubscription.id.desc())
        )
        if not sub or (sub.ends_at and sub.ends_at < today_s):
            continue
        tu, tq = int(sub.tokens_used or 0), int(sub.token_quota or 0)
        ru, rq = int(sub.requests_used or 0), int(sub.request_quota or 0)
        token_used_total += tu
        token_quota_total += tq
        request_used_total += ru
        request_quota_total += rq
        tp = round(100 * tu / max(tq, 1), 1)
        rp = round(100 * ru / max(rq, 1), 1)
        token_pct_max = max(token_pct_max, tp, rp)
        alert = tp >= 80 or rp >= 80
        if alert:
            quota_alert_count += 1
        quota_tenants.append(
            {
                "id": t.id,
                "name": t.name,
                "token_pct": tp,
                "request_pct": rp,
                "ends_at": sub.ends_at,
                "alert": alert,
            }
        )
    quota_tenants.sort(key=lambda x: max(x["token_pct"], x["request_pct"]), reverse=True)

    return DashboardOut(
        users=users,
        teachers=teachers,
        students=students,
        courses=courses,
        classes=classes,
        questions=questions,
        orders=orders_n,
        checkins_today=checkins_today,
        active_members=len(member_uids),
        revenue_total=revenue_total,
        revenue_today=revenue_today,
        orders_today=orders_today,
        feedback_open=feedback_open,
        grade_pending=grade_pending,
        learning_minutes_30d=learning_minutes_30d,
        checkin_trend=[{"day": d, "count": checkin_counter.get(d, 0)} for d in days],
        user_growth=[{"day": d, "count": user_counter.get(d, 0)} for d in days],
        order_trend=[
            {"day": d, "count": order_counter.get(d, 0), "amount": round(order_amount.get(d, 0), 2)}
            for d in days
        ],
        activity_dist={
            "course_watch": course_watch,
            "checkin": checkin_all,
            "submission": submissions,
            "vocab": vocab,
        },
        top_students=ranked[:10],
        top_classes=class_ranks[:10],
        recent_audits=[AuditOut.model_validate(a) for a in audits],
        tenant_count=tenant_count,
        quota_alert_count=quota_alert_count,
        token_used_total=token_used_total,
        token_quota_total=token_quota_total,
        request_used_total=request_used_total,
        request_quota_total=request_quota_total,
        token_pct_max=token_pct_max,
        quota_tenants=quota_tenants[:5],
    )


@router.get("/students", response_model=List[StudentOpsOut])
def student_ops(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> List[StudentOpsOut]:
    """系统管理员：学员账号 / 会员 / 活跃度一览。"""
    students = list(db.scalars(select(User).where(User.role == "student").order_by(User.id.desc())))
    checkin_by: Counter = Counter(c.user_id for c in db.scalars(select(Checkin)).all())
    sub_by: Counter = Counter(s.user_id for s in db.scalars(select(Submission)).all())
    wrong_by: Counter = Counter(
        w.user_id
        for w in db.scalars(select(WrongItem).where(WrongItem.mastered.is_(False))).all()
    )
    prog_by: Counter = Counter(
        p.user_id
        for p in db.scalars(select(ProgressItem).where(ProgressItem.status == "completed")).all()
    )
    orders = list(db.scalars(select(Order).where(Order.status == "paid")))
    orders_by: dict[int, list] = defaultdict(list)
    for o in orders:
        orders_by[o.user_id].append(o)

    # plan names
    from ..models import MembershipPlan

    plans = {p.id: p.name for p in db.scalars(select(MembershipPlan)).all()}

    # last active approx from latest checkin / submission / progress
    last_map: dict[int, str] = {}
    for c in db.scalars(select(Checkin)).all():
        prev = last_map.get(c.user_id)
        if not prev or c.day > prev:
            last_map[c.user_id] = c.day

    out: List[StudentOpsOut] = []
    for u in students:
        u_orders = orders_by.get(u.id, [])
        plan_name = ""
        if u_orders:
            latest = max(u_orders, key=lambda x: x.id)
            plan_name = plans.get(latest.plan_id or 0, "会员")
        score = checkin_by[u.id] * 3 + sub_by[u.id] * 5 + prog_by[u.id] * 2
        out.append(
            StudentOpsOut(
                id=u.id,
                email=u.email,
                display_name=u.display_name,
                status=u.status,
                tags=u.tags or "",
                created_at=u.created_at.isoformat() if u.created_at else None,
                checkins=checkin_by[u.id],
                submissions=sub_by[u.id],
                wrong_open=wrong_by[u.id],
                progress_done=prog_by[u.id],
                orders=len(u_orders),
                paid_amount=round(sum(o.amount for o in u_orders), 2),
                member_plan=plan_name,
                is_member=bool(u_orders),
                last_active=last_map.get(u.id),
                activity_score=score,
            )
        )
    out.sort(key=lambda x: x.activity_score, reverse=True)
    return out


@router.get("/audits", response_model=list[AuditOut])
def list_audits(_: User = Depends(require_staff), db: Session = Depends(get_db)) -> list[AuditLog]:
    return list(db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(100)))
