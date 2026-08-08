from __future__ import annotations
import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..db import get_db
from ..models import ProgressItem, User
from ..schemas import CourseSummary, ProgressItemOut, ProgressSummaryOut, ProgressUpsertIn, UserOut

router = APIRouter(prefix="/progress", tags=["progress"])

# 用于计算完成百分比的「应完成条目」目录（与前端 courses.ts 对齐）
COURSE_CATALOG: dict[str, list[str]] = {
    "geometry-lab": [
        "cube",
        "box",
        "pyramid",
        "random-7",
        "ellipse_dot_range",
        "ellipse_chord_range",
        "ellipse_area_max",
        "ellipse_slopeprod_const",
        "parabola_dot_const",
        "hyperbola_ecc_range",
    ],
    "english-coach": ["cafe", "school", "travel", "interview"],
    "ai-coding": [
        "what-is-ai",
        "variables",
        "loops",
        "draw",
        "mini-bot",
        "project",
    ],
    # AI多智能体互动课堂：按课堂 id 统计
    "classroom": [
        "line-plane-angle",
    ],
}


def _item_out(row: ProgressItem) -> ProgressItemOut:
    try:
        meta = json.loads(row.meta_json or "{}")
    except json.JSONDecodeError:
        meta = {}
    return ProgressItemOut(
        course_id=row.course_id,
        item_id=row.item_id,
        status=row.status,
        score=row.score,
        meta=meta if isinstance(meta, dict) else {},
        updated_at=row.updated_at,
    )


def _summaries(items: list[ProgressItem]) -> list[CourseSummary]:
    by_course: dict[str, list[ProgressItem]] = {}
    for it in items:
        by_course.setdefault(it.course_id, []).append(it)

    out: list[CourseSummary] = []
    for course_id, catalog in COURSE_CATALOG.items():
        rows = by_course.get(course_id, [])
        completed_ids = {r.item_id for r in rows if r.status == "completed"}
        started_ids = {r.item_id for r in rows}
        total = len(catalog)
        completed = len(completed_ids & set(catalog))
        started = len(started_ids & set(catalog))
        percent = int(round(completed * 100 / total)) if total else 0
        out.append(
            CourseSummary(
                course_id=course_id,
                total_items=total,
                started=started,
                completed=completed,
                percent=percent,
            )
        )
    return out


@router.get("/me", response_model=ProgressSummaryOut)
def my_progress(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ProgressSummaryOut:
    rows = list(db.scalars(select(ProgressItem).where(ProgressItem.user_id == user.id)))
    return ProgressSummaryOut(
        user=UserOut.model_validate(user),
        courses=_summaries(rows),
        items=[_item_out(r) for r in rows],
    )


@router.post("/upsert", response_model=ProgressItemOut)
def upsert_progress(
    body: ProgressUpsertIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProgressItemOut:
    row = db.scalar(
        select(ProgressItem).where(
            ProgressItem.user_id == user.id,
            ProgressItem.course_id == body.course_id,
            ProgressItem.item_id == body.item_id,
        )
    )
    meta_json = json.dumps(body.meta, ensure_ascii=False)
    if row is None:
        row = ProgressItem(
            user_id=user.id,
            course_id=body.course_id,
            item_id=body.item_id,
            status=body.status,
            score=body.score,
            meta_json=meta_json,
        )
        db.add(row)
    else:
        # completed 不可被 started 降级
        if not (row.status == "completed" and body.status == "started"):
            row.status = body.status
        row.score = max(row.score, body.score)
        row.meta_json = meta_json
    db.commit()
    db.refresh(row)
    return _item_out(row)
