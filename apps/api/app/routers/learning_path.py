from __future__ import annotations

from collections import Counter
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..db import get_db
from ..models import LabPage, Question, User, WrongItem

router = APIRouter(prefix="/learning-path", tags=["learning-path"])


class PathStep(BaseModel):
    kind: str  # lab|practice|vocab|reading|wrongbook
    title: str
    reason: str
    link: str
    priority: int = 1
    meta: dict = Field(default_factory=dict)


class PathOut(BaseModel):
    weak_points: List[str]
    steps: List[PathStep]
    summary: str


@router.get("/me", response_model=PathOut)
def my_learning_path(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PathOut:
    wrongs = list(
        db.scalars(
            select(WrongItem).where(WrongItem.user_id == user.id, WrongItem.mastered.is_(False))
        )
    )
    kp_counter: Counter = Counter()
    for w in wrongs:
        for part in (w.knowledge_points or "未标注").split(","):
            key = part.strip() or "未标注"
            kp_counter[key] += 1
    weak = [k for k, _ in kp_counter.most_common(5)]

    steps: List[PathStep] = []
    priority = 1

    if wrongs:
        steps.append(
            PathStep(
                kind="wrongbook",
                title=f"攻克 {len(wrongs)} 道未掌握错题",
                reason="错题本仍有待攻克题目",
                link="/wrongbook",
                priority=priority,
                meta={"count": len(wrongs)},
            )
        )
        priority += 1

    for kp in weak[:3]:
        page = db.scalar(
            select(LabPage).where(LabPage.knowledge_points.contains(kp)).order_by(LabPage.id)
        )
        if page:
            steps.append(
                PathStep(
                    kind="lab",
                    title=f"复习课页：{page.title}",
                    reason=f"薄弱点「{kp}」对应可视化课页",
                    link=f"/courses/geometry-lab/{page.page_key}",
                    priority=priority,
                    meta={"page_key": page.page_key, "knowledge_point": kp},
                )
            )
            priority += 1

        q = db.scalar(
            select(Question)
            .where(Question.knowledge_points.contains(kp), Question.type != "essay")
            .order_by(Question.difficulty, Question.id)
        )
        if q:
            steps.append(
                PathStep(
                    kind="practice",
                    title=f"巩固练习 · {kp}",
                    reason="同源推荐题，即时核对并回写错题本",
                    link=f"/recommend?ids={q.id}",
                    priority=priority,
                    meta={"question_id": q.id, "knowledge_point": kp},
                )
            )
            priority += 1

    steps.append(
        PathStep(
            kind="vocab",
            title="今日单词",
            reason="保持英语日课节奏",
            link="/courses/love-words",
            priority=priority,
        )
    )
    priority += 1
    steps.append(
        PathStep(
            kind="reading",
            title="每日美文",
            reason="阅读输入与语感",
            link="/reading",
            priority=priority,
        )
    )

    if not weak:
        summary = "暂无明显薄弱点，建议按「单词 → 美文 → 推荐练习」保持节奏。"
    else:
        summary = f"建议优先处理薄弱点：{'、'.join(weak[:3])}，再完成日课。"

    return PathOut(weak_points=weak, steps=steps, summary=summary)
