from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit_util import write_audit
from ..auth import get_current_user
from ..db import get_db
from ..models import Course, MembershipPlan, Order, User
from ..rbac import require_admin
from ..schemas import OrderIn, OrderOut, PlanOut

router = APIRouter(tags=["orders"])


@router.get("/membership-plans", response_model=list[PlanOut])
def list_plans(db: Session = Depends(get_db)) -> list[MembershipPlan]:
    return list(db.scalars(select(MembershipPlan).order_by(MembershipPlan.price)))


@router.get("/orders", response_model=list[OrderOut])
def list_orders(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[Order]:
    return list(db.scalars(select(Order).order_by(Order.id.desc())))


@router.get("/orders/me", response_model=list[OrderOut])
def my_orders(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[Order]:
    return list(db.scalars(select(Order).where(Order.user_id == user.id).order_by(Order.id.desc())))


@router.post("/orders", response_model=OrderOut)
def create_order(
    body: OrderIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Order:
    amount = 0.0
    if body.plan_id:
        plan = db.get(MembershipPlan, body.plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="套餐不存在")
        amount = plan.price
    elif body.course_id:
        course = db.get(Course, body.course_id)
        if not course:
            raise HTTPException(status_code=404, detail="课程不存在")
        amount = course.price
    else:
        raise HTTPException(status_code=400, detail="请选择套餐或课程")

    order = Order(
        user_id=user.id,
        plan_id=body.plan_id,
        course_id=body.course_id,
        amount=amount,
        status="paid",  # 演示：模拟支付成功
    )
    db.add(order)
    write_audit(db, user=user, action="order.create", resource=str(amount), detail="模拟支付")
    db.commit()
    db.refresh(order)
    return order
