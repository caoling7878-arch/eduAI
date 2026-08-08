from __future__ import annotations

import json
from collections import Counter
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit_util import write_audit
from ..db import get_db
from ..models import FeedbackTicket, GradeTask, User, WorkflowRule, WorkflowRun
from ..rbac import require_staff
from ..services.workflow_engine import dispatch_event, seed_workflow_rules

router = APIRouter(prefix="/workflows", tags=["workflows"])


class RuleIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    event: str = Field(min_length=1, max_length=64)
    action: str = Field(default="notify_staff", max_length=64)
    enabled: bool = True
    description: str = ""
    config_json: str = "{}"


class RuleOut(BaseModel):
    id: int
    name: str
    enabled: bool
    event: str
    action: str
    description: str
    config_json: str
    created_at: Optional[str] = None


class RunOut(BaseModel):
    id: int
    rule_id: Optional[int]
    event: str
    status: str
    message: str
    payload_json: str
    created_at: Optional[str] = None


def _rule_out(r: WorkflowRule) -> RuleOut:
    return RuleOut(
        id=r.id,
        name=r.name,
        enabled=r.enabled,
        event=r.event,
        action=r.action,
        description=r.description,
        config_json=r.config_json,
        created_at=r.created_at.isoformat() if r.created_at else None,
    )


def _run_out(r: WorkflowRun) -> RunOut:
    return RunOut(
        id=r.id,
        rule_id=r.rule_id,
        event=r.event,
        status=r.status,
        message=r.message,
        payload_json=r.payload_json,
        created_at=r.created_at.isoformat() if r.created_at else None,
    )


@router.get("/overview")
def workflow_overview(_: User = Depends(require_staff), db: Session = Depends(get_db)) -> dict:
    """教学工作流看板：批改阶段 + 反馈工单 + 规则摘要。"""
    seed_workflow_rules(db)
    grades = list(db.scalars(select(GradeTask)))
    by_status = Counter(t.status or "unknown" for t in grades)
    by_qc = Counter(t.qc_status or "none" for t in grades)

    tickets = list(db.scalars(select(FeedbackTicket)))
    ticket_by = Counter(t.status or "open" for t in tickets)

    rules = list(db.scalars(select(WorkflowRule)))
    enabled = sum(1 for r in rules if r.enabled)

    stages = [
        {
            "key": "pending",
            "label": "待 AI 批改",
            "count": by_status.get("pending", 0),
            "link": "/grading?status=pending",
        },
        {
            "key": "ai_done",
            "label": "待教师复核",
            "count": by_status.get("ai_done", 0)
            + by_status.get("ai_graded", 0)
            + by_status.get("ai_scored", 0),
            "link": "/grading?status=ai_done",
        },
        {
            "key": "teacher_reviewed",
            "label": "教师已复核",
            "count": by_status.get("teacher_reviewed", 0),
            "link": "/grading?status=teacher_reviewed",
        },
        {
            "key": "qc_sampled",
            "label": "质检抽样待审",
            "count": by_qc.get("sampled", 0) + by_qc.get("pending", 0),
            "link": "/grading",
        },
        {
            "key": "feedback_open",
            "label": "开放反馈工单",
            "count": ticket_by.get("open", 0) + ticket_by.get("processing", 0),
            "link": "/feedback",
        },
    ]

    return {
        "stages": stages,
        "grade_status": dict(by_status),
        "qc_status": dict(by_qc),
        "feedback_status": dict(ticket_by),
        "total_grade_tasks": len(grades),
        "rules_total": len(rules),
        "rules_enabled": enabled,
        "note": "工作流 = 看板聚合 + 事件规则引擎（批改/反馈/积压催办可自动通知）。",
    }


@router.get("/events")
def list_events(_: User = Depends(require_staff)) -> list:
    return [
        {"id": "grade.ai_done", "label": "AI 批改完成"},
        {"id": "grade.reviewed", "label": "教师复核完成"},
        {"id": "feedback.created", "label": "新反馈工单"},
        {"id": "check.pending_grades", "label": "巡检：批改积压"},
    ]


@router.get("/actions")
def list_actions(_: User = Depends(require_staff)) -> list:
    return [
        {"id": "notify_staff", "label": "通知教职工"},
        {"id": "notify_user", "label": "通知学员"},
        {"id": "noop", "label": "仅记日志"},
    ]


@router.get("/rules", response_model=List[RuleOut])
def list_rules(_: User = Depends(require_staff), db: Session = Depends(get_db)) -> List[RuleOut]:
    seed_workflow_rules(db)
    rows = list(db.scalars(select(WorkflowRule).order_by(WorkflowRule.id)))
    return [_rule_out(r) for r in rows]


@router.post("/rules", response_model=RuleOut)
def create_rule(
    body: RuleIn,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> RuleOut:
    try:
        json.loads(body.config_json or "{}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail="config_json 不是合法 JSON") from e
    r = WorkflowRule(
        name=body.name.strip(),
        event=body.event.strip(),
        action=body.action.strip(),
        enabled=body.enabled,
        description=body.description,
        config_json=body.config_json or "{}",
    )
    db.add(r)
    write_audit(db, user=admin, action="workflow.rule.create", resource=body.name)
    db.commit()
    db.refresh(r)
    return _rule_out(r)


@router.patch("/rules/{rid}", response_model=RuleOut)
def update_rule(
    rid: int,
    body: RuleIn,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> RuleOut:
    r = db.get(WorkflowRule, rid)
    if not r:
        raise HTTPException(status_code=404, detail="规则不存在")
    try:
        json.loads(body.config_json or "{}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail="config_json 不是合法 JSON") from e
    r.name = body.name.strip()
    r.event = body.event.strip()
    r.action = body.action.strip()
    r.enabled = body.enabled
    r.description = body.description
    r.config_json = body.config_json or "{}"
    write_audit(db, user=admin, action="workflow.rule.update", resource=str(rid))
    db.commit()
    db.refresh(r)
    return _rule_out(r)


@router.post("/rules/{rid}/toggle")
def toggle_rule(
    rid: int,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> dict:
    r = db.get(WorkflowRule, rid)
    if not r:
        raise HTTPException(status_code=404, detail="规则不存在")
    r.enabled = not r.enabled
    write_audit(db, user=admin, action="workflow.rule.toggle", resource=f"{rid}:{r.enabled}")
    db.commit()
    return {"id": rid, "enabled": r.enabled}


@router.get("/runs", response_model=List[RunOut])
def list_runs(
    limit: int = 50,
    _: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> List[RunOut]:
    lim = max(1, min(limit, 200))
    rows = list(db.scalars(select(WorkflowRun).order_by(WorkflowRun.id.desc()).limit(lim)))
    return [_run_out(r) for r in rows]


@router.post("/dispatch/{event}")
def manual_dispatch(
    event: str,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> dict:
    seed_workflow_rules(db)
    results = dispatch_event(db, event, {"triggered_by": admin.id, "manual": True})
    write_audit(db, user=admin, action="workflow.dispatch", resource=event, detail=str(results)[:300])
    db.commit()
    return {"event": event, "results": results}
