from __future__ import annotations

import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit_util import write_audit
from ..db import get_db
from ..models import DatasetSample, FineTuneJob, GradeTask, Question, User, WrongItem
from ..rbac import require_admin, require_staff
from ..services.finetune import advance_finetune_job, create_finetune_job, job_out

router = APIRouter(prefix="/datasets", tags=["datasets"])


class SampleOut(BaseModel):
    id: int
    source: str
    question_id: Optional[int]
    user_id: Optional[int]
    knowledge_points: str
    payload: dict
    exported: bool
    created_at: Optional[str] = None


class FineTuneCreateIn(BaseModel):
    name: str = "样本微调任务"
    sample_ids: Optional[List[int]] = None
    unexported_only: bool = True
    limit: int = Field(default=200, ge=1, le=2000)
    base_model: str = "gpt-4o-mini"
    provider: str = "openai_compatible"


def _collect(db: Session) -> int:
    """从错题与评分差异回流样本（幂等：按 source+question+user 去重粗略）。"""
    existing_keys = set()
    for s in db.scalars(select(DatasetSample)):
        try:
            p = json.loads(s.payload_json or "{}")
        except json.JSONDecodeError:
            p = {}
        existing_keys.add((s.source, s.question_id, s.user_id, p.get("fingerprint")))

    added = 0
    for w in db.scalars(select(WrongItem).where(WrongItem.mastered.is_(False))):
        q = db.get(Question, w.question_id)
        fp = f"wrong:{w.id}"
        key = ("wrong", w.question_id, w.user_id, fp)
        if key in existing_keys:
            continue
        payload = {
            "fingerprint": fp,
            "stem": q.stem if q else "",
            "type": q.type if q else "",
            "user_answer": w.user_answer,
            "correct_answer": w.correct_answer,
            "analysis": q.analysis if q else "",
        }
        db.add(
            DatasetSample(
                source="wrong",
                question_id=w.question_id,
                user_id=w.user_id,
                knowledge_points=w.knowledge_points,
                payload_json=json.dumps(payload, ensure_ascii=False),
            )
        )
        existing_keys.add(key)
        added += 1

    for t in db.scalars(select(GradeTask).where(GradeTask.status == "teacher_reviewed")):
        if t.ai_score is None or t.teacher_score is None:
            continue
        if abs(float(t.ai_score) - float(t.teacher_score)) < 0.5:
            continue
        q = db.get(Question, t.question_id)
        fp = f"grade:{t.id}"
        key = ("grade_diff", t.question_id, t.user_id, fp)
        if key in existing_keys:
            continue
        payload = {
            "fingerprint": fp,
            "stem": q.stem if q else "",
            "answer_text": t.answer_text,
            "ai_score": t.ai_score,
            "teacher_score": t.teacher_score,
            "ai_feedback": t.ai_feedback,
            "teacher_feedback": t.teacher_feedback,
            "max_score": t.max_score,
        }
        db.add(
            DatasetSample(
                source="grade_diff",
                question_id=t.question_id,
                user_id=t.user_id,
                knowledge_points=q.knowledge_points if q else "",
                payload_json=json.dumps(payload, ensure_ascii=False),
            )
        )
        existing_keys.add(key)
        added += 1

    db.commit()
    return added


@router.post("/sync")
def sync_samples(admin: User = Depends(require_staff), db: Session = Depends(get_db)) -> dict:
    n = _collect(db)
    write_audit(db, user=admin, action="dataset.sync", resource=str(n))
    db.commit()
    return {"status": "ok", "added": n}


@router.get("/samples", response_model=List[SampleOut])
def list_samples(
    source: str = "",
    exported: Optional[bool] = Query(default=None),
    _: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> List[SampleOut]:
    stmt = select(DatasetSample).order_by(DatasetSample.id.desc()).limit(200)
    if source:
        stmt = stmt.where(DatasetSample.source == source)
    if exported is not None:
        stmt = stmt.where(DatasetSample.exported.is_(exported))
    out: List[SampleOut] = []
    for s in db.scalars(stmt):
        try:
            payload = json.loads(s.payload_json or "{}")
        except json.JSONDecodeError:
            payload = {}
        out.append(
            SampleOut(
                id=s.id,
                source=s.source,
                question_id=s.question_id,
                user_id=s.user_id,
                knowledge_points=s.knowledge_points,
                payload=payload if isinstance(payload, dict) else {},
                exported=s.exported,
                created_at=s.created_at.isoformat() if s.created_at else None,
            )
        )
    return out


@router.get("/export")
def export_samples(
    format: str = Query(default="jsonl"),
    source: str = Query(default=""),
    unexported_only: bool = Query(default=False),
    mark_exported: bool = True,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    _collect(db)
    stmt = select(DatasetSample).order_by(DatasetSample.id)
    if source:
        stmt = stmt.where(DatasetSample.source == source)
    if unexported_only:
        stmt = stmt.where(DatasetSample.exported.is_(False))
    rows = list(db.scalars(stmt))
    items = []
    for s in rows:
        try:
            payload = json.loads(s.payload_json or "{}")
        except json.JSONDecodeError:
            payload = {}
        items.append(
            {
                "id": s.id,
                "source": s.source,
                "question_id": s.question_id,
                "user_id": s.user_id,
                "knowledge_points": s.knowledge_points,
                "payload": payload,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
        )
        if mark_exported:
            s.exported = True
    write_audit(db, user=admin, action="dataset.export", resource=str(len(items)))
    db.commit()

    if format == "json":
        return items
    body = "\n".join(json.dumps(it, ensure_ascii=False) for it in items) + ("\n" if items else "")
    return PlainTextResponse(body, media_type="application/x-ndjson")


@router.get("/finetune/jobs")
def list_finetune_jobs(
    _: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> list:
    rows = list(db.scalars(select(FineTuneJob).order_by(FineTuneJob.id.desc()).limit(50)))
    return [job_out(j) for j in rows]


@router.post("/finetune/jobs")
def create_job(
    body: FineTuneCreateIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    _collect(db)
    try:
        job = create_finetune_job(
            db,
            user=admin,
            name=body.name,
            sample_ids=body.sample_ids,
            unexported_only=body.unexported_only,
            limit=body.limit,
            base_model=body.base_model,
            provider=body.provider,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    write_audit(db, user=admin, action="finetune.create", resource=str(job.id))
    db.commit()
    return job_out(job)


@router.post("/finetune/jobs/{job_id}/advance")
def advance_job(
    job_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    job = db.get(FineTuneJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    job = advance_finetune_job(db, job)
    write_audit(db, user=admin, action="finetune.advance", resource=f"{job.id}:{job.status}")
    db.commit()
    return job_out(job)


@router.get("/finetune/jobs/{job_id}")
def get_job(
    job_id: int,
    _: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> dict:
    job = db.get(FineTuneJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    return job_out(job)
