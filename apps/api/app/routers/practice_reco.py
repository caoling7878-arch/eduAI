from __future__ import annotations

import json
from collections import Counter
from typing import List, Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..db import get_db
from ..models import ClassMember, Notification, Question, User, WrongItem
from ..rbac import require_staff

router = APIRouter(prefix="/practice", tags=["practice-recommend"])


class RecoQuestion(BaseModel):
    id: int
    type: str
    stem: str
    options: List[str] = Field(default_factory=list)
    knowledge_points: str
    difficulty: int
    reason: str


class RecoOut(BaseModel):
    weak_points: List[str]
    questions: List[RecoQuestion]


class PushIn(BaseModel):
    user_ids: List[int] = Field(default_factory=list)
    class_id: Optional[int] = None
    title: str = "薄弱点练习提醒"
    body: str = "系统根据你的错题为你准备了巩固练习，去练习中心看看吧。"
    question_ids: List[int] = Field(default_factory=list)
    link: Optional[str] = None


def _q(q: Question, reason: str) -> RecoQuestion:
    try:
        options = json.loads(q.options_json or "[]")
    except json.JSONDecodeError:
        options = []
    return RecoQuestion(
        id=q.id,
        type=q.type,
        stem=q.stem,
        options=options if isinstance(options, list) else [],
        knowledge_points=q.knowledge_points,
        difficulty=q.difficulty,
        reason=reason,
    )


@router.get("/recommend", response_model=RecoOut)
def recommend(
    limit: int = 8,
    ids: str = Query(default="", description="逗号分隔题目 ID，优先作为推送深链题单"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecoOut:
    forced_ids: List[int] = []
    for part in ids.split(","):
        part = part.strip()
        if part.isdigit():
            forced_ids.append(int(part))

    if forced_ids:
        questions: List[RecoQuestion] = []
        for qid in forced_ids[:limit]:
            q = db.get(Question, qid)
            if q and q.type != "essay":
                questions.append(_q(q, "老师推送题单"))
        return RecoOut(weak_points=[], questions=questions)

    wrongs = list(
        db.scalars(
            select(WrongItem).where(WrongItem.user_id == user.id, WrongItem.mastered.is_(False))
        )
    )
    kp_counter: Counter = Counter()
    wrong_qids = set()
    for w in wrongs:
        wrong_qids.add(w.question_id)
        for part in (w.knowledge_points or "未标注").split(","):
            key = part.strip() or "未标注"
            kp_counter[key] += 1

    weak = [k for k, _ in kp_counter.most_common(5)]
    if not weak:
        rows = list(db.scalars(select(Question).order_by(Question.difficulty, Question.id).limit(limit)))
        return RecoOut(weak_points=[], questions=[_q(q, "每日巩固推荐") for q in rows])

    candidates: List[RecoQuestion] = []
    seen = set()
    for kp in weak:
        rows = list(
            db.scalars(
                select(Question)
                .where(Question.knowledge_points.contains(kp), Question.type != "essay")
                .order_by(Question.difficulty, Question.id)
                .limit(limit)
            )
        )
        for q in rows:
            if q.id in seen:
                continue
            reason = f"错题同源巩固 · {kp}" if q.id in wrong_qids else f"薄弱知识点推荐 · {kp}"
            seen.add(q.id)
            candidates.append(_q(q, reason))
            if len(candidates) >= limit:
                break
        if len(candidates) >= limit:
            break

    return RecoOut(weak_points=weak, questions=candidates[:limit])


@router.post("/push")
def push_practice(
    body: PushIn,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> dict:
    targets = set(body.user_ids)
    if body.class_id:
        mids = list(db.scalars(select(ClassMember.user_id).where(ClassMember.class_id == body.class_id)))
        targets.update(mids)
    if not targets:
        raise HTTPException(status_code=400, detail="请指定学员或班级")

    qids = [qid for qid in body.question_ids if db.get(Question, qid)]
    if not qids and body.class_id:
        # 班级推送：取该班学员最常见薄弱知识点上的题目作深链
        member_ids = list(targets)
        wrongs = list(
            db.scalars(
                select(WrongItem).where(
                    WrongItem.user_id.in_(member_ids), WrongItem.mastered.is_(False)
                )
            )
        )
        kp_counter: Counter = Counter()
        for w in wrongs:
            for part in (w.knowledge_points or "").split(","):
                key = part.strip()
                if key:
                    kp_counter[key] += 1
        top_kp = kp_counter.most_common(1)[0][0] if kp_counter else "立体几何"
        rows = list(
            db.scalars(
                select(Question)
                .where(Question.knowledge_points.contains(top_kp), Question.type != "essay")
                .order_by(Question.difficulty, Question.id)
                .limit(5)
            )
        )
        qids = [q.id for q in rows]

    if body.link:
        link = body.link
    elif qids:
        link = "/recommend?" + urlencode({"ids": ",".join(str(i) for i in qids), "from": "push"})
    else:
        link = "/recommend?from=push"

    for uid in targets:
        db.add(
            Notification(
                user_id=uid,
                title=body.title,
                body=body.body,
                link=link,
                kind="study",
            )
        )
    db.commit()
    return {"status": "ok", "pushed": len(targets), "link": link, "question_ids": qids}
