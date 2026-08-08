"""简易工作流编排：事件触发规则 → 通知等动作。"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import GradeTask, Notification, User, WorkflowRule, WorkflowRun

# 内置规则种子
DEFAULT_RULES = [
    {
        "name": "AI 批改完成 → 通知教师",
        "event": "grade.ai_done",
        "action": "notify_staff",
        "description": "主观题 AI 初评完成后，提醒教师进入复核台。",
        "config_json": json.dumps(
            {"title": "待复核：AI 已完成初评", "link": "/grading", "roles": ["admin", "teacher"]},
            ensure_ascii=False,
        ),
    },
    {
        "name": "教师复核完成 → 通知学员",
        "event": "grade.reviewed",
        "action": "notify_user",
        "description": "教师复核后向学员发送结果提醒（补充已有通知）。",
        "config_json": json.dumps(
            {"title": "作业复核提醒", "link": "/practice", "kind": "grade"},
            ensure_ascii=False,
        ),
    },
    {
        "name": "新反馈工单 → 通知管理员",
        "event": "feedback.created",
        "action": "notify_staff",
        "description": "学员提交反馈后通知管理员/教师处理。",
        "config_json": json.dumps(
            {"title": "新反馈工单", "link": "/feedback", "roles": ["admin", "teacher"]},
            ensure_ascii=False,
        ),
    },
    {
        "name": "积压批改超阈值 → 催办",
        "event": "check.pending_grades",
        "action": "notify_staff",
        "description": "手动或巡检时，若待复核任务超过阈值则催办。",
        "config_json": json.dumps(
            {
                "title": "批改积压提醒",
                "link": "/grading",
                "roles": ["admin", "teacher"],
                "threshold": 5,
            },
            ensure_ascii=False,
        ),
    },
]


def seed_workflow_rules(db: Session) -> dict:
    n = db.scalar(select(func.count()).select_from(WorkflowRule)) or 0
    if n > 0:
        return {"seeded": False, "total": n}
    for raw in DEFAULT_RULES:
        db.add(WorkflowRule(**raw, enabled=True))
    db.commit()
    total = db.scalar(select(func.count()).select_from(WorkflowRule)) or 0
    return {"seeded": True, "total": total}


def _cfg(rule: WorkflowRule) -> Dict[str, Any]:
    try:
        data = json.loads(rule.config_json or "{}")
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _staff_ids(db: Session, roles: Optional[List[str]] = None) -> List[int]:
    roles = roles or ["admin", "teacher"]
    return [
        u.id
        for u in db.scalars(
            select(User).where(User.status == "active", User.role.in_(roles))
        )
    ]


def _log(
    db: Session,
    *,
    rule: Optional[WorkflowRule],
    event: str,
    payload: dict,
    status: str,
    message: str,
) -> WorkflowRun:
    run = WorkflowRun(
        rule_id=rule.id if rule else None,
        event=event,
        payload_json=json.dumps(payload, ensure_ascii=False)[:4000],
        status=status,
        message=message[:500],
    )
    db.add(run)
    return run


def _notify_staff(db: Session, rule: WorkflowRule, payload: dict) -> str:
    cfg = _cfg(rule)
    roles = cfg.get("roles") or ["admin", "teacher"]
    title = str(cfg.get("title") or rule.name)
    body = str(payload.get("body") or cfg.get("body") or rule.description or "")
    link = str(cfg.get("link") or "/workflows")
    kind = str(cfg.get("kind") or "system")
    ids = _staff_ids(db, list(roles))
    for uid in ids:
        db.add(
            Notification(
                user_id=uid,
                title=title,
                body=body[:500],
                link=link,
                kind=kind,
            )
        )
    return f"已通知 {len(ids)} 位教职工"


def _notify_user(db: Session, rule: WorkflowRule, payload: dict) -> str:
    cfg = _cfg(rule)
    uid = payload.get("user_id")
    if not uid:
        return "跳过：无 user_id"
    title = str(payload.get("title") or cfg.get("title") or rule.name)
    body = str(payload.get("body") or cfg.get("body") or rule.description or "")
    link = str(payload.get("link") or cfg.get("link") or "/")
    kind = str(cfg.get("kind") or "study")
    db.add(
        Notification(
            user_id=int(uid),
            title=title,
            body=body[:500],
            link=link,
            kind=kind,
        )
    )
    return f"已通知学员 #{uid}"


def dispatch_event(db: Session, event: str, payload: Optional[dict] = None) -> List[dict]:
    """触发事件，执行所有启用规则。调用方负责 commit。"""
    payload = payload or {}
    rules = list(
        db.scalars(
            select(WorkflowRule).where(
                WorkflowRule.enabled.is_(True), WorkflowRule.event == event
            )
        )
    )
    results: List[dict] = []
    if not rules:
        _log(db, rule=None, event=event, payload=payload, status="skipped", message="无匹配规则")
        return [{"status": "skipped", "message": "无匹配规则"}]

    for rule in rules:
        # 阈值类：check.pending_grades
        if event == "check.pending_grades":
            cfg = _cfg(rule)
            threshold = int(cfg.get("threshold") or 5)
            pending = (
                db.scalar(
                    select(func.count())
                    .select_from(GradeTask)
                    .where(GradeTask.status.in_(["pending", "ai_done", "ai_graded", "ai_scored"]))
                )
                or 0
            )
            if pending < threshold:
                _log(
                    db,
                    rule=rule,
                    event=event,
                    payload={**payload, "pending": pending, "threshold": threshold},
                    status="skipped",
                    message=f"积压 {pending} < 阈值 {threshold}",
                )
                results.append({"rule_id": rule.id, "status": "skipped", "message": f"积压 {pending}"})
                continue
            payload = {
                **payload,
                "body": f"当前待处理批改任务 {pending} 条（阈值 {threshold}），请及时处理。",
                "pending": pending,
            }

        try:
            if rule.action == "notify_staff":
                msg = _notify_staff(db, rule, payload)
            elif rule.action == "notify_user":
                msg = _notify_user(db, rule, payload)
            elif rule.action == "noop":
                msg = "noop"
            else:
                msg = f"未知动作 {rule.action}"
                _log(db, rule=rule, event=event, payload=payload, status="error", message=msg)
                results.append({"rule_id": rule.id, "status": "error", "message": msg})
                continue
            _log(db, rule=rule, event=event, payload=payload, status="ok", message=msg)
            results.append({"rule_id": rule.id, "status": "ok", "message": msg})
        except Exception as e:
            _log(db, rule=rule, event=event, payload=payload, status="error", message=str(e)[:200])
            results.append({"rule_id": rule.id, "status": "error", "message": str(e)[:200]})
    return results
