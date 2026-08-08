"""小学数学计算专项练习 API。"""

from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..db import get_db
from ..models import MathCalcDaily, MathCalcItem, Question, SiteSetting, User, WrongItem
from ..services.math_calc import (
    GRADE_META,
    answers_equal,
    build_bank,
    kp_label,
    meta_for,
    normalize_answer,
    rewrite_mixed_to_slash,
)

router = APIRouter(prefix="/math-calc", tags=["math-calc"])


class PrefsIn(BaseModel):
    grade: int = Field(default=1, ge=1, le=6)
    daily_count: int = Field(default=20, ge=10, le=100)


class PrefsOut(PrefsIn):
    topic: str = ""
    prompt_hint: str = ""


class ItemOut(BaseModel):
    id: int
    grade: int
    topic: str
    stem: str
    prompt_hint: str = ""
    answer_kind: str


class TodayOut(BaseModel):
    day: str
    grade: int
    topic: str
    prompt_hint: str
    submitted: bool
    correct_count: int = 0
    total_count: int = 0
    elapsed_seconds: int = 0
    items: List[ItemOut]
    answers: Dict[str, str] = Field(default_factory=dict)
    results: Dict[str, dict] = Field(default_factory=dict)


class SubmitIn(BaseModel):
    answers: Dict[str, str] = Field(default_factory=dict)
    elapsed_seconds: int = Field(default=0, ge=0, le=24 * 3600)


class DraftIn(BaseModel):
    answers: Dict[str, str] = Field(default_factory=dict)
    elapsed_seconds: int = Field(default=0, ge=0, le=24 * 3600)


class FixIn(BaseModel):
    item_id: int
    answer: str


class HistoryRow(BaseModel):
    day: str
    grade: int
    topic: str
    correct_count: int
    total_count: int
    elapsed_seconds: int
    accuracy: float
    submitted: bool


def _pref_key(user_id: int) -> str:
    return f"math_calc_prefs:{user_id}"


def _load_prefs(db: Session, user_id: int) -> PrefsIn:
    row = db.scalar(select(SiteSetting).where(SiteSetting.key == _pref_key(user_id)))
    if not row or not row.value:
        return PrefsIn()
    try:
        data = json.loads(row.value)
        return PrefsIn(
            grade=int(data.get("grade", 1)),
            daily_count=int(data.get("daily_count", 20)),
        )
    except Exception:
        return PrefsIn()


def _ensure_question(db: Session, item: MathCalcItem) -> Question:
    if item.question_id:
        q = db.get(Question, item.question_id)
        if q:
            return q
    kp = kp_label(item.grade, item.topic)
    existing = db.scalar(
        select(Question).where(Question.stem == item.stem, Question.knowledge_points == kp)
    )
    if existing:
        item.question_id = existing.id
        return existing
    q = Question(
        type="blank",
        stem=item.stem,
        options_json="[]",
        answer=item.answer,
        analysis=f"参考答案：{item.answer}",
        knowledge_points=kp,
        difficulty=item.grade,
    )
    db.add(q)
    db.flush()
    item.question_id = q.id
    return q


def _migrate_fraction_stems(db: Session) -> int:
    """把库内带「又」的分数题干/答案改成 a/b，异分母加减题型保留。"""
    fixed = 0
    for item in db.scalars(select(MathCalcItem)):
        new_stem = rewrite_mixed_to_slash(item.stem)
        new_ans = rewrite_mixed_to_slash(item.answer)
        if new_stem != item.stem or new_ans != item.answer:
            # 避免唯一约束冲突：若目标 stem 已存在则跳过改 stem
            if new_stem != item.stem:
                clash = db.scalar(
                    select(MathCalcItem).where(
                        MathCalcItem.grade == item.grade,
                        MathCalcItem.stem == new_stem,
                        MathCalcItem.id != item.id,
                    )
                )
                if clash:
                    item.answer = new_ans
                else:
                    item.stem = new_stem
                    item.answer = new_ans
            else:
                item.answer = new_ans
            fixed += 1
    if fixed:
        db.commit()
    return fixed


def seed_math_calc_bank(db: Session, per_grade: int = 500, force: bool = False) -> dict:
    count = db.scalar(select(func.count()).select_from(MathCalcItem)) or 0
    if count > 0 and not force:
        migrated = _migrate_fraction_stems(db)
        total = db.scalar(select(func.count()).select_from(MathCalcItem)) or 0
        return {"status": "ok", "total": total, "seeded": False, "migrated": migrated}
    if force:
        for row in db.scalars(select(MathCalcItem)):
            db.delete(row)
        db.commit()

    bank = build_bank(per_grade=per_grade)
    added = 0
    for raw in bank:
        stem = rewrite_mixed_to_slash(raw.stem)
        answer = rewrite_mixed_to_slash(raw.answer)
        exists = db.scalar(
            select(MathCalcItem).where(
                MathCalcItem.grade == raw.grade, MathCalcItem.stem == stem
            )
        )
        if exists:
            continue
        db.add(
            MathCalcItem(
                grade=raw.grade,
                topic=raw.topic,
                stem=stem,
                answer=answer,
                answer_kind=raw.answer_kind,
                source=raw.source,
            )
        )
        added += 1
    db.commit()
    migrated = _migrate_fraction_stems(db)
    total = db.scalar(select(func.count()).select_from(MathCalcItem)) or 0
    return {"status": "ok", "total": total, "added": added, "seeded": True, "migrated": migrated}


@router.get("/grades")
def list_grades(db: Session = Depends(get_db)) -> list:
    out = []
    for m in GRADE_META:
        c = (
            db.scalar(
                select(func.count()).select_from(MathCalcItem).where(MathCalcItem.grade == m["grade"])
            )
            or 0
        )
        out.append({**m, "bank_count": c})
    return out


@router.get("/prefs", response_model=PrefsOut)
def get_prefs(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> PrefsOut:
    p = _load_prefs(db, user.id)
    m = meta_for(p.grade)
    return PrefsOut(grade=p.grade, daily_count=p.daily_count, topic=m["topic"], prompt_hint=m["prompt_hint"])


@router.put("/prefs", response_model=PrefsOut)
def put_prefs(
    body: PrefsIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PrefsOut:
    key = _pref_key(user.id)
    raw = json.dumps({"grade": body.grade, "daily_count": body.daily_count}, ensure_ascii=False)
    row = db.scalar(select(SiteSetting).where(SiteSetting.key == key))
    if row:
        row.value = raw
    else:
        db.add(SiteSetting(key=key, value=raw))
    # 改设置后，若今日未提交则重建今日卷
    today_s = date.today().isoformat()
    daily = db.scalar(
        select(MathCalcDaily).where(MathCalcDaily.user_id == user.id, MathCalcDaily.day == today_s)
    )
    if daily and not daily.submitted:
        db.delete(daily)
    db.commit()
    m = meta_for(body.grade)
    return PrefsOut(
        grade=body.grade,
        daily_count=body.daily_count,
        topic=m["topic"],
        prompt_hint=m["prompt_hint"],
    )


def _pick_today_items(db: Session, grade: int, n: int) -> List[MathCalcItem]:
    """按年级随机抽题；数据库侧 RANDOM，避免全表载入内存。"""
    rows = list(
        db.scalars(
            select(MathCalcItem)
            .where(MathCalcItem.grade == grade)
            .order_by(func.random())
            .limit(max(1, n))
        )
    )
    if not rows:
        raise HTTPException(status_code=400, detail="该年级题库为空，请稍后重试或联系管理员")
    return rows


@router.get("/today", response_model=TodayOut)
def get_today(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> TodayOut:
    prefs = _load_prefs(db, user.id)
    m = meta_for(prefs.grade)
    today_s = date.today().isoformat()
    daily = db.scalar(
        select(MathCalcDaily).where(MathCalcDaily.user_id == user.id, MathCalcDaily.day == today_s)
    )
    if not daily:
        items = _pick_today_items(db, prefs.grade, prefs.daily_count)
        daily = MathCalcDaily(
            user_id=user.id,
            day=today_s,
            grade=prefs.grade,
            topic=m["topic"],
            item_ids_json=json.dumps([it.id for it in items]),
            total_count=len(items),
        )
        db.add(daily)
        db.commit()
        db.refresh(daily)

    ids = json.loads(daily.item_ids_json or "[]")
    items_map = {
        it.id: it
        for it in db.scalars(select(MathCalcItem).where(MathCalcItem.id.in_(ids or [0])))
    }
    ordered = [items_map[i] for i in ids if i in items_map]
    answers = json.loads(daily.answers_json or "{}")
    results = json.loads(daily.results_json or "{}")
    return TodayOut(
        day=daily.day,
        grade=daily.grade,
        topic=daily.topic or m["topic"],
        prompt_hint=m["prompt_hint"],
        submitted=daily.submitted,
        correct_count=daily.correct_count,
        total_count=daily.total_count or len(ordered),
        elapsed_seconds=getattr(daily, "elapsed_seconds", 0) or 0,
        items=[
            ItemOut(
                id=it.id,
                grade=it.grade,
                topic=it.topic,
                stem=it.stem,
                prompt_hint=m["prompt_hint"],
                answer_kind=it.answer_kind,
            )
            for it in ordered
        ],
        answers={str(k): str(v) for k, v in answers.items()},
        results={str(k): v for k, v in results.items()},
    )


@router.post("/today/draft")
def save_draft(
    body: DraftIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """自动保存未提交答案与已用时，支持刷新后续作。"""
    today_s = date.today().isoformat()
    daily = db.scalar(
        select(MathCalcDaily).where(MathCalcDaily.user_id == user.id, MathCalcDaily.day == today_s)
    )
    if not daily:
        raise HTTPException(status_code=404, detail="今日练习尚未生成")
    if daily.submitted:
        return {"status": "ok", "skipped": True, "reason": "already_submitted"}

    clean = {str(k): str(v)[:120] for k, v in (body.answers or {}).items() if str(v).strip()}
    daily.answers_json = json.dumps(clean, ensure_ascii=False)
    # 取较大值，避免旧定时器回写把时间打回去
    prev = int(getattr(daily, "elapsed_seconds", 0) or 0)
    daily.elapsed_seconds = max(prev, int(body.elapsed_seconds or 0))
    db.commit()
    return {
        "status": "ok",
        "saved_answers": len(clean),
        "elapsed_seconds": daily.elapsed_seconds,
    }


@router.post("/today/submit", response_model=TodayOut)
def submit_today(
    body: SubmitIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TodayOut:
    today_s = date.today().isoformat()
    daily = db.scalar(
        select(MathCalcDaily).where(MathCalcDaily.user_id == user.id, MathCalcDaily.day == today_s)
    )
    if not daily:
        raise HTTPException(status_code=404, detail="今日练习尚未生成")
    if daily.submitted:
        raise HTTPException(status_code=400, detail="今日练习已提交，请先订正错题")

    ids = json.loads(daily.item_ids_json or "[]")
    items = {
        it.id: it
        for it in db.scalars(select(MathCalcItem).where(MathCalcItem.id.in_(ids or [0])))
    }
    results: dict = {}
    correct_n = 0
    for iid in ids:
        it = items.get(iid)
        if not it:
            continue
        raw = (body.answers or {}).get(str(iid), "")
        ok = answers_equal(raw, it.answer, it.answer_kind)
        results[str(iid)] = {
            "correct": ok,
            "user_answer": raw,
            "correct_answer": it.answer if not ok else "",
            "fixed": False,
        }
        if ok:
            correct_n += 1
        else:
            q = _ensure_question(db, it)
            existing = db.scalar(
                select(WrongItem).where(
                    WrongItem.user_id == user.id,
                    WrongItem.question_id == q.id,
                    WrongItem.mastered.is_(False),
                )
            )
            if existing:
                existing.user_answer = raw
                existing.correct_answer = it.answer
            else:
                db.add(
                    WrongItem(
                        user_id=user.id,
                        question_id=q.id,
                        user_answer=raw,
                        correct_answer=it.answer,
                        knowledge_points=kp_label(it.grade, it.topic),
                        source="math_calc",
                        mastered=False,
                    )
                )

    daily.answers_json = json.dumps(body.answers or {}, ensure_ascii=False)
    daily.results_json = json.dumps(results, ensure_ascii=False)
    daily.submitted = True
    daily.correct_count = correct_n
    daily.total_count = len(ids)
    daily.elapsed_seconds = int(body.elapsed_seconds or 0)
    db.commit()
    return get_today(user, db)


@router.post("/fix")
def fix_answer(
    body: FixIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    today_s = date.today().isoformat()
    daily = db.scalar(
        select(MathCalcDaily).where(MathCalcDaily.user_id == user.id, MathCalcDaily.day == today_s)
    )
    if not daily or not daily.submitted:
        raise HTTPException(status_code=400, detail="请先提交今日练习")

    it = db.get(MathCalcItem, body.item_id)
    if not it:
        raise HTTPException(status_code=404, detail="题目不存在")
    ids = json.loads(daily.item_ids_json or "[]")
    if it.id not in ids:
        raise HTTPException(status_code=400, detail="非今日题目")

    ok = answers_equal(body.answer, it.answer, it.answer_kind)
    results = json.loads(daily.results_json or "{}")
    entry = results.get(str(it.id), {})
    entry["user_answer"] = body.answer
    entry["fixed"] = bool(ok)
    entry["correct"] = bool(ok) or bool(entry.get("correct"))
    if ok:
        entry["correct_answer"] = ""
        # 掌握错题本
        q = _ensure_question(db, it)
        for w in db.scalars(
            select(WrongItem).where(
                WrongItem.user_id == user.id,
                WrongItem.question_id == q.id,
                WrongItem.mastered.is_(False),
            )
        ):
            w.mastered = True
        # 重算正确数：首次对 + 已订正
        results[str(it.id)] = entry
        correct_n = sum(
            1
            for iid in ids
            if results.get(str(iid), {}).get("correct") or results.get(str(iid), {}).get("fixed")
        )
        daily.correct_count = correct_n
    else:
        entry["correct_answer"] = it.answer
        results[str(it.id)] = entry

    answers = json.loads(daily.answers_json or "{}")
    answers[str(it.id)] = body.answer
    daily.answers_json = json.dumps(answers, ensure_ascii=False)
    daily.results_json = json.dumps(results, ensure_ascii=False)
    db.commit()
    return {
        "correct": ok,
        "message": "订正正确，已从错题本标记掌握" if ok else "仍不正确，请再试一次",
        "correct_answer": "" if ok else it.answer,
        "normalized": normalize_answer(body.answer, it.answer_kind),
    }


def _calc_streak(db: Session, user_id: int) -> int:
    days = {
        d.day
        for d in db.scalars(
            select(MathCalcDaily).where(
                MathCalcDaily.user_id == user_id, MathCalcDaily.submitted.is_(True)
            )
        )
    }
    if not days:
        return 0
    streak = 0
    cursor = date.today()
    if cursor.isoformat() not in days:
        cursor = cursor - timedelta(days=1)
    while cursor.isoformat() in days:
        streak += 1
        cursor = cursor - timedelta(days=1)
    return streak


@router.get("/history", response_model=List[HistoryRow])
def history(
    limit: int = 14,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[HistoryRow]:
    lim = max(1, min(limit, 60))
    rows = list(
        db.scalars(
            select(MathCalcDaily)
            .where(MathCalcDaily.user_id == user.id, MathCalcDaily.submitted.is_(True))
            .order_by(MathCalcDaily.day.desc())
            .limit(lim)
        )
    )
    out: List[HistoryRow] = []
    for d in rows:
        total = d.total_count or 0
        acc = round((d.correct_count / total) * 100, 1) if total else 0.0
        out.append(
            HistoryRow(
                day=d.day,
                grade=d.grade,
                topic=d.topic,
                correct_count=d.correct_count,
                total_count=total,
                elapsed_seconds=getattr(d, "elapsed_seconds", 0) or 0,
                accuracy=acc,
                submitted=d.submitted,
            )
        )
    return out


@router.get("/summary")
def summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    prefs = _load_prefs(db, user.id)
    m = meta_for(prefs.grade)
    bank = (
        db.scalar(
            select(func.count()).select_from(MathCalcItem).where(MathCalcItem.grade == prefs.grade)
        )
        or 0
    )
    today_s = date.today().isoformat()
    daily = db.scalar(
        select(MathCalcDaily).where(MathCalcDaily.user_id == user.id, MathCalcDaily.day == today_s)
    )
    wrong_open = (
        db.scalar(
            select(func.count())
            .select_from(WrongItem)
            .where(
                WrongItem.user_id == user.id,
                WrongItem.mastered.is_(False),
                WrongItem.source == "math_calc",
            )
        )
        or 0
    )
    completed_days = (
        db.scalar(
            select(func.count())
            .select_from(MathCalcDaily)
            .where(MathCalcDaily.user_id == user.id, MathCalcDaily.submitted.is_(True))
        )
        or 0
    )
    streak = _calc_streak(db, user.id)
    elapsed = getattr(daily, "elapsed_seconds", 0) if daily else 0
    return {
        "course": "小学数学计算专项练习",
        "grade": prefs.grade,
        "topic": m["topic"],
        "daily_count": prefs.daily_count,
        "bank_count": bank,
        "today_submitted": bool(daily and daily.submitted),
        "today_correct": daily.correct_count if daily else 0,
        "today_total": daily.total_count if daily else 0,
        "today_elapsed_seconds": elapsed or 0,
        "wrong_open": wrong_open,
        "prompt_hint": m["prompt_hint"],
        "streak_days": streak,
        "completed_days": completed_days,
        "need_reminder": (not bool(daily and daily.submitted)) or int(wrong_open) > 0,
        "need_practice": not bool(daily and daily.submitted),
        "need_fix": int(wrong_open) > 0,
    }
