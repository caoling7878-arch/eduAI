"""外部微调任务：由回流样本组装 Chat JSONL，对接外部训练服务（演示级）。"""

from __future__ import annotations

import json
import os
import uuid
from typing import Iterable, List, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import DatasetSample, FineTuneJob, User

STATUS_FLOW = ("queued", "submitted", "running", "succeeded")


def sample_to_messages(sample: DatasetSample) -> Optional[dict]:
    try:
        payload = json.loads(sample.payload_json or "{}")
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        return None
    stem = (payload.get("stem") or "").strip()
    if not stem:
        return None

    if sample.source == "wrong":
        user_ans = payload.get("user_answer") or ""
        correct = payload.get("correct_answer") or ""
        analysis = payload.get("analysis") or ""
        assistant = (
            f"正确答案：{correct}\n"
            f"讲解：{analysis or '请对照知识点订正。'}\n"
            f"（学员原答：{user_ans}）"
        )
    else:
        # grade_diff：以教师反馈为监督信号
        teacher_fb = payload.get("teacher_feedback") or payload.get("ai_feedback") or ""
        score = payload.get("teacher_score")
        max_s = payload.get("max_score") or 10
        answer = payload.get("answer_text") or ""
        assistant = (
            f"评分：{score}/{max_s}\n"
            f"评语：{teacher_fb or '请按评分标准给分并指出要点。'}"
        )
        stem = f"{stem}\n\n学生作答：{answer}"

    return {
        "messages": [
            {
                "role": "system",
                "content": "你是严谨的学科助教，按知识点给出正确答法与简洁讲解。",
            },
            {"role": "user", "content": stem[:4000]},
            {"role": "assistant", "content": assistant[:4000]},
        ]
    }


def build_jsonl_lines(samples: Iterable[DatasetSample]) -> List[str]:
    lines: List[str] = []
    for s in samples:
        row = sample_to_messages(s)
        if row:
            lines.append(json.dumps(row, ensure_ascii=False))
    return lines


def create_finetune_job(
    db: Session,
    *,
    user: User,
    name: str,
    sample_ids: Optional[List[int]] = None,
    unexported_only: bool = True,
    limit: int = 200,
    base_model: str = "gpt-4o-mini",
    provider: str = "openai_compatible",
) -> FineTuneJob:
    stmt = select(DatasetSample).order_by(DatasetSample.id.desc()).limit(max(10, min(limit, 2000)))
    if sample_ids:
        stmt = select(DatasetSample).where(DatasetSample.id.in_(sample_ids))
    elif unexported_only:
        stmt = stmt.where(DatasetSample.exported.is_(False))
    rows = list(db.scalars(stmt))
    if not rows:
        raise ValueError("没有可用样本，请先回流或取消「仅未导出」筛选")

    lines = build_jsonl_lines(rows)
    if not lines:
        raise ValueError("样本无法组装为训练对话，请检查 payload")

    preview = "\n".join(lines[:3])
    if len(lines) > 3:
        preview += f"\n…共 {len(lines)} 行"

    job = FineTuneJob(
        name=(name or f"微调任务 {len(rows)} 条").strip()[:120],
        status="queued",
        provider=provider,
        base_model=base_model[:120],
        sample_ids_json=json.dumps([r.id for r in rows]),
        sample_count=len(lines),
        training_preview=preview,
        external_job_id=f"ft-demo-{uuid.uuid4().hex[:12]}",
        progress_pct=5,
        created_by=user.id,
    )
    db.add(job)
    for r in rows:
        r.exported = True
    db.flush()

    webhook = (os.getenv("FINETUNE_WEBHOOK_URL") or "").strip()
    if webhook:
        try:
            httpx.post(
                webhook,
                json={
                    "job_id": job.id,
                    "external_job_id": job.external_job_id,
                    "base_model": job.base_model,
                    "sample_count": job.sample_count,
                    "provider": job.provider,
                    "jsonl_lines": lines[:50],  # 演示只推前 50 行
                },
                timeout=8.0,
            )
            job.webhook_status = "sent"
            job.status = "submitted"
            job.progress_pct = 20
        except Exception as e:  # noqa: BLE001
            job.webhook_status = "error"
            job.error = str(e)[:300]
    else:
        job.webhook_status = "skipped"

    db.commit()
    db.refresh(job)
    return job


def advance_finetune_job(db: Session, job: FineTuneJob) -> FineTuneJob:
    """演示推进：queued → submitted → running → succeeded。"""
    if job.status in ("succeeded", "failed", "cancelled"):
        return job
    try:
        idx = STATUS_FLOW.index(job.status)
    except ValueError:
        job.status = "queued"
        idx = 0
    if idx >= len(STATUS_FLOW) - 1:
        return job
    nxt = STATUS_FLOW[idx + 1]
    job.status = nxt
    job.progress_pct = { "queued": 5, "submitted": 25, "running": 70, "succeeded": 100 }.get(nxt, 50)
    if nxt == "succeeded":
        job.error = ""
    db.commit()
    db.refresh(job)
    return job


def job_out(job: FineTuneJob) -> dict:
    try:
        ids = json.loads(job.sample_ids_json or "[]")
    except json.JSONDecodeError:
        ids = []
    return {
        "id": job.id,
        "name": job.name,
        "status": job.status,
        "provider": job.provider,
        "base_model": job.base_model,
        "sample_count": job.sample_count,
        "sample_ids": ids if isinstance(ids, list) else [],
        "training_preview": job.training_preview,
        "external_job_id": job.external_job_id,
        "webhook_status": job.webhook_status,
        "progress_pct": job.progress_pct,
        "error": job.error,
        "created_by": job.created_by,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }
