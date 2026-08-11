from __future__ import annotations

import json
import math
import random
from datetime import date, timedelta
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..db import get_db
from ..models import (
    MembershipPlan,
    Order,
    SiteSetting,
    User,
    VocabDailyLog,
    VocabProgress,
    VocabReward,
    VocabWord,
)
from ..rbac import require_staff
from ..services.vocab_images import photo_url
from ..services.vocab_schedule import schedule_ok, schedule_wrong, star_for_streak
from ..services.verb_forms import conjugations_for
from ..services.word_image import resolve_theme
from ..services.word_morphology import morph_for, morph_json_dumps

router = APIRouter(prefix="/vocab", tags=["vocab"])

BANKS = [
    {"id": "zhongkao_800", "name": "中学生必背单词", "available": True, "desc": "北京中考频率精选 800 词"},
    {"id": "cet4", "name": "大学英语四级", "available": False, "desc": "即将上线"},
    {"id": "cet6", "name": "大学英语六级", "available": False, "desc": "即将上线"},
    {"id": "ielts", "name": "雅思", "available": False, "desc": "即将上线"},
    {"id": "toefl", "name": "托福", "available": False, "desc": "即将上线"},
]

STARS_PER_MONTH_MEMBER = 30


class MorphSegment(BaseModel):
    text: str
    type: str = "root"
    gloss: str = ""
    icon: str = "shape"
    color: str = "#0F6B5C"


class MeaningItem(BaseModel):
    pos: str = ""
    text: str = ""


class VerbForms(BaseModel):
    ing: str = ""
    past: str = ""
    past_participle: str = ""


class WordOut(BaseModel):
    id: int
    word: str
    phonetic: str
    meaning: str
    meanings: List[MeaningItem] = Field(default_factory=list)
    example: str
    level: str
    status: str = "new"
    review_count: int = 0
    image_key: str = ""
    morph_story: str = ""
    segments: List[MorphSegment] = Field(default_factory=list)
    is_long: bool = False
    bank: str = "zhongkao_800"
    pos: str = ""
    scene: str = ""
    frequency: str = ""
    role: str = "new"  # new|review|wrong
    wrong_count: int = 0
    next_review_date: str = ""
    is_verb: bool = False
    verb_forms: Optional[VerbForms] = None
    image_url: Optional[str] = None


class WordIn(BaseModel):
    word: str
    phonetic: str = ""
    meaning: str = ""
    example: str = ""
    level: str = "A2"
    day_tag: str = ""
    morphology_json: str = ""
    image_key: str = ""
    bank: str = "zhongkao_800"
    pos: str = ""
    scene: str = ""
    frequency: str = ""
    meanings_json: str = "[]"


class ProgressIn(BaseModel):
    status: str = Field(pattern="^(learning|known|hard)$")


class VocabPrefs(BaseModel):
    bank: str = "zhongkao_800"
    daily_count: int = Field(default=20, ge=5, le=100)
    show_morph: bool = True
    auto_speak: bool = False
    # 兼容旧字段
    level_max: str = "B2"
    prefer_long: bool = True


class QuizItem(BaseModel):
    word_id: int
    word: str
    prompt: str
    options: List[str]
    # 不返回 correct 给前端提交前


class QuizSubmitIn(BaseModel):
    answers: dict = Field(default_factory=dict)  # word_id -> option text


def _pref_key(user_id: int) -> str:
    return f"vocab_pref:{user_id}"


def _load_prefs(db: Session, user_id: int) -> VocabPrefs:
    row = db.scalar(select(SiteSetting).where(SiteSetting.key == _pref_key(user_id)))
    if not row or not row.value:
        return VocabPrefs()
    try:
        data = json.loads(row.value)
        # 迁移旧 daily_count 3-30
        if "daily_count" in data:
            data["daily_count"] = max(5, min(100, int(data["daily_count"])))
        return VocabPrefs(**{k: v for k, v in data.items() if k in VocabPrefs.model_fields})
    except (json.JSONDecodeError, TypeError, ValueError):
        return VocabPrefs()


def _parse_meanings(w: VocabWord) -> List[MeaningItem]:
    try:
        raw = json.loads(w.meanings_json or "[]")
        if isinstance(raw, list) and raw:
            return [MeaningItem(pos=str(x.get("pos") or w.pos or ""), text=str(x.get("text") or "")) for x in raw]
    except (json.JSONDecodeError, TypeError):
        pass
    parts = [p.strip() for p in (w.meaning or "").replace(";", "；").split("；") if p.strip()]
    if not parts:
        parts = [w.meaning or ""]
    return [MeaningItem(pos=w.pos or "", text=p) for p in parts]


def _out(w: VocabWord, prog: Optional[VocabProgress] = None, role: str = "new") -> WordOut:
    meanings = _parse_meanings(w)
    morph = morph_for(w.word, w.morphology_json or "", meaning=w.meaning or "")
    theme = resolve_theme(w.word, w.meaning or "", w.image_key or morph.get("image_key") or w.word)
    segments = [MorphSegment(**s) for s in morph.get("segments") or []]
    forms = conjugations_for(w.word, w.pos or "")
    img = photo_url(w.word)
    return WordOut(
        id=w.id,
        word=w.word,
        phonetic=w.phonetic or "",
        meaning=w.meaning,
        meanings=meanings,
        example=w.example,
        level=w.level,
        status=prog.status if prog else "new",
        review_count=prog.review_count if prog else 0,
        image_key=theme,
        morph_story=str(morph.get("story") or ""),
        segments=segments,
        is_long=len(w.word) >= 7 or len(segments) >= 2,
        bank=w.bank or "zhongkao_800",
        pos=w.pos or "",
        scene=w.scene or "",
        frequency=w.frequency or "",
        role=role,
        wrong_count=prog.wrong_count if prog else 0,
        next_review_date=prog.next_review_date if prog else "",
        is_verb=forms is not None,
        verb_forms=VerbForms(**forms) if forms else None,
        image_url=img,
    )


def _get_or_create_reward(db: Session, user_id: int) -> VocabReward:
    row = db.scalar(select(VocabReward).where(VocabReward.user_id == user_id))
    if row:
        month = date.today().strftime("%Y-%m")
        if row.month_key != month:
            row.month_key = month
            row.stars_month = 0
        return row
    row = VocabReward(user_id=user_id, month_key=date.today().strftime("%Y-%m"))
    db.add(row)
    db.flush()
    return row


def _bank_count(db: Session, bank: str) -> int:
    return int(db.scalar(select(func.count()).select_from(VocabWord).where(VocabWord.bank == bank)) or 0)


@router.get("/banks")
def list_banks() -> list:
    return BANKS


@router.get("/prefs", response_model=VocabPrefs)
def get_prefs(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> VocabPrefs:
    return _load_prefs(db, user.id)


@router.put("/prefs", response_model=VocabPrefs)
def put_prefs(
    body: VocabPrefs,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VocabPrefs:
    bank_meta = next((b for b in BANKS if b["id"] == body.bank), None)
    if not bank_meta or not bank_meta["available"]:
        raise HTTPException(status_code=400, detail="该词库暂未开放，请选择「中学生必背单词」")
    old = _load_prefs(db, user.id)
    key = _pref_key(user.id)
    raw = body.model_dump_json()
    row = db.scalar(select(SiteSetting).where(SiteSetting.key == key))
    if row:
        row.value = raw
    else:
        db.add(SiteSetting(key=key, value=raw))
    # 考试分类或每日数量变更后，丢弃当日固定词单，按新设置重建
    if old.bank != body.bank or old.daily_count != body.daily_count:
        _invalidate_today_pack(db, user.id)
    db.commit()
    return body


def _invalidate_today_pack(db: Session, user_id: int) -> None:
    today = date.today().isoformat()
    log = db.scalar(
        select(VocabDailyLog).where(VocabDailyLog.user_id == user_id, VocabDailyLog.day == today)
    )
    if log:
        log.pack_json = ""
        log.daily_count = 0


def _get_or_create_daily_log(db: Session, user_id: int, today_s: str, bank: str) -> VocabDailyLog:
    log = db.scalar(
        select(VocabDailyLog).where(VocabDailyLog.user_id == user_id, VocabDailyLog.day == today_s)
    )
    if log:
        return log
    log = VocabDailyLog(user_id=user_id, day=today_s, bank=bank)
    db.add(log)
    db.flush()
    return log


def _pack_from_log(
    db: Session, user: User, log: VocabDailyLog, prefs: VocabPrefs
) -> Optional[List[WordOut]]:
    """若当日已有与当前设置匹配的固定词单，则原样返回（学习写进度后也不换词）。"""
    if not (log.pack_json or "").strip():
        return None
    if log.bank != prefs.bank or int(log.daily_count or 0) != int(prefs.daily_count):
        return None
    try:
        items = json.loads(log.pack_json)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(items, list):
        return None
    # 空列表表示当日无词可学（词库学完且无到期复习），仍视为有效缓存
    if not items:
        return []
    ids = [int(x["id"]) for x in items if isinstance(x, dict) and x.get("id") is not None]
    if not ids:
        return None
    words = {
        w.id: w
        for w in db.scalars(
            select(VocabWord).where(VocabWord.id.in_(ids), VocabWord.bank == prefs.bank)
        )
    }
    if len(words) != len(ids):
        return None
    progs = {
        p.word_id: p
        for p in db.scalars(
            select(VocabProgress).where(
                VocabProgress.user_id == user.id, VocabProgress.word_id.in_(ids)
            )
        )
    }
    out: List[WordOut] = []
    for item in items:
        wid = int(item["id"])
        w = words.get(wid)
        if not w:
            return None
        role = str(item.get("role") or "new")
        out.append(_out(w, progs.get(wid), role=role))
    return out


def _save_today_pack(
    log: VocabDailyLog, prefs: VocabPrefs, ordered: List[tuple]
) -> None:
    log.bank = prefs.bank
    log.daily_count = prefs.daily_count
    log.pack_json = json.dumps(
        [{"id": w.id, "role": role} for w, role in ordered],
        ensure_ascii=False,
    )
    log.new_count = sum(1 for _, r in ordered if r == "new")
    log.review_count = sum(1 for _, r in ordered if r != "new")


@router.get("/course/summary")
def course_summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    prefs = _load_prefs(db, user.id)
    total = _bank_count(db, prefs.bank)
    learned = int(
        db.scalar(
            select(func.count())
            .select_from(VocabProgress)
            .join(VocabWord, VocabWord.id == VocabProgress.word_id)
            .where(VocabProgress.user_id == user.id, VocabWord.bank == prefs.bank)
        )
        or 0
    )
    daily = prefs.daily_count
    days_needed = math.ceil(total / daily) if daily and total else 0
    days_left = math.ceil(max(total - learned, 0) / daily) if daily else 0
    reward = _get_or_create_reward(db, user.id)
    today = date.today().isoformat()
    log = db.scalar(
        select(VocabDailyLog).where(VocabDailyLog.user_id == user.id, VocabDailyLog.day == today)
    )
    db.commit()
    bank_name = next((b["name"] for b in BANKS if b["id"] == prefs.bank), prefs.bank)
    return {
        "course": "我爱背单词",
        "bank": prefs.bank,
        "bank_name": bank_name,
        "daily_count": daily,
        "bank_total": total,
        "learned": learned,
        "days_needed": days_needed,
        "days_left": days_left,
        "percent": round(learned * 100 / total, 1) if total else 0,
        "stars_total": reward.stars_total,
        "stars_month": reward.stars_month,
        "streak_days": reward.streak_days,
        "stars_to_member": max(STARS_PER_MONTH_MEMBER - reward.stars_month, 0),
        "today_completed": bool(log and log.completed),
        "today_stars": log.stars_earned if log else 0,
        "need_reminder": not bool(log and log.completed),
    }


@router.get("/today", response_model=List[WordOut])
def today_words(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[WordOut]:
    """兼容旧接口：返回今日课表（复习优先 + 新词）。"""
    return _build_today_pack(user, db)


@router.get("/course/today", response_model=List[WordOut])
def course_today(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[WordOut]:
    return _build_today_pack(user, db)


def _build_today_pack(user: User, db: Session) -> List[WordOut]:
    """按所选考试词库 + 每日数量 + 艾宾浩斯到期复习生成今日词单。

    词单在当日固定：学习过程中写入进度不会改换题目；仅换词库/每日数量或跨日才重建。
    新词按词库课程顺序（sort_order），不随机抽取。
    """
    prefs = _load_prefs(db, user.id)
    today = date.today().isoformat()
    bank = prefs.bank
    daily_new = prefs.daily_count
    log = _get_or_create_daily_log(db, user.id, today, bank)

    cached = _pack_from_log(db, user, log, prefs)
    if cached is not None:
        return cached

    # 已学进度（仅当前词库）
    bank_words = list(
        db.scalars(
            select(VocabWord)
            .where(VocabWord.bank == bank)
            .order_by(VocabWord.sort_order, VocabWord.id)
        )
    )
    bank_ids = [w.id for w in bank_words]
    progs = {
        p.word_id: p
        for p in db.scalars(
            select(VocabProgress).where(
                VocabProgress.user_id == user.id,
                VocabProgress.word_id.in_(bank_ids) if bank_ids else False,
            )
        )
    } if bank_ids else {}

    # 1) 艾宾浩斯到期：错题优先，再普通复习
    wrong_due: List[VocabWord] = []
    due: List[VocabWord] = []
    for w in bank_words:
        p = progs.get(w.id)
        if not p:
            continue
        due_date = p.next_review_date or today
        if due_date <= today:
            if (p.wrong_count or 0) > 0 or p.last_result == "wrong" or p.status == "hard":
                wrong_due.append(w)
            else:
                due.append(w)

    # 2) 新词：该考试词库中尚无进度的词，按课程顺序取 daily_count 个
    new_words = [w for w in bank_words if w.id not in progs][:daily_new]

    pack: List[tuple] = []
    for w in wrong_due:
        pack.append((w, "wrong"))
    for w in due:
        pack.append((w, "review"))
    for w in new_words:
        pack.append((w, "new"))

    # 复习量控制：最多 daily_new * 2 条复习；错词与到期复习合计截断
    reviews = [(w, r) for w, r in pack if r != "new"]
    news = [(w, r) for w, r in pack if r == "new"]
    reviews = reviews[: max(daily_new * 2, 10)]
    ordered = reviews + news

    _save_today_pack(log, prefs, ordered)
    db.commit()

    out: List[WordOut] = []
    for w, role in ordered:
        out.append(_out(w, progs.get(w.id), role=role))
    return out


@router.post("/{wid}/progress", response_model=WordOut)
def upsert_progress(
    wid: int,
    body: ProgressIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WordOut:
    w = db.get(VocabWord, wid)
    if not w:
        raise HTTPException(status_code=404, detail="单词不存在")
    today = date.today()
    prog = db.scalar(
        select(VocabProgress).where(VocabProgress.user_id == user.id, VocabProgress.word_id == wid)
    )
    if not prog:
        step, interval, nxt = schedule_ok(0, today)
        prog = VocabProgress(
            user_id=user.id,
            word_id=wid,
            status=body.status,
            review_count=1,
            ease_step=step,
            interval_days=interval,
            next_review_date=nxt,
            last_result="ok",
        )
        db.add(prog)
    else:
        prog.status = body.status
        prog.review_count += 1
        if body.status == "hard":
            step, interval, nxt = schedule_wrong(today)
            prog.ease_step = step
            prog.interval_days = interval
            prog.next_review_date = nxt
            prog.last_result = "wrong"
        else:
            step, interval, nxt = schedule_ok(prog.ease_step or 0, today)
            prog.ease_step = step
            prog.interval_days = interval
            prog.next_review_date = nxt
            prog.last_result = "ok"
    db.commit()
    return _out(w, prog, role="review")


@router.get("/course/quiz", response_model=List[QuizItem])
def course_quiz(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> List[QuizItem]:
    pack = _build_today_pack(user, db)
    if not pack:
        return []
    prefs = _load_prefs(db, user.id)
    # 干扰项仅从同一考试词库抽取（按课程顺序取前缀池，再打乱选项）
    pool = list(
        db.scalars(
            select(VocabWord)
            .where(VocabWord.bank == prefs.bank)
            .order_by(VocabWord.sort_order, VocabWord.id)
            .limit(200)
        )
    )
    meanings_pool = [p.meaning for p in pool if p.meaning]
    items: List[QuizItem] = []
    for w in pack:
        correct = w.meanings[0].text if w.meanings else w.meaning
        distractors = [m for m in meanings_pool if m != w.meaning and correct not in m]
        random.shuffle(distractors)
        opts = [correct] + distractors[:3]
        while len(opts) < 4:
            opts.append(f"（干扰项{len(opts)}）")
        random.shuffle(opts)
        items.append(
            QuizItem(
                word_id=w.id,
                word=w.word,
                prompt=f"「{w.word}」的中文意思是？",
                options=opts,
            )
        )
    return items


@router.post("/course/quiz/submit")
def submit_quiz(
    body: QuizSubmitIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    prefs = _load_prefs(db, user.id)
    pack = _build_today_pack(user, db)
    today = date.today()
    today_s = today.isoformat()
    correct_n = 0
    wrong_ids: List[int] = []
    details = []

    for w in pack:
        ans = str(body.answers.get(str(w.id)) or body.answers.get(w.id) or "").strip()
        # 任一完整义项命中即正确
        ok_texts = {w.meaning}
        for m in w.meanings:
            ok_texts.add(m.text)
            ok_texts.add(w.meaning)
        # 选项可能是完整 meaning 字符串
        is_ok = ans == w.meaning or ans in ok_texts or any(ans == m.text for m in w.meanings)
        # 也接受「分号拼接」首义
        if w.meanings and ans == w.meanings[0].text:
            is_ok = True

        prog = db.scalar(
            select(VocabProgress).where(VocabProgress.user_id == user.id, VocabProgress.word_id == w.id)
        )
        if not prog:
            prog = VocabProgress(user_id=user.id, word_id=w.id, status="learning", review_count=0)
            db.add(prog)
            db.flush()

        prog.review_count += 1
        if is_ok:
            correct_n += 1
            step, interval, nxt = schedule_ok(prog.ease_step or 0, today)
            prog.ease_step = step
            prog.interval_days = interval
            prog.next_review_date = nxt
            prog.last_result = "ok"
            if prog.status != "hard":
                prog.status = "known" if (prog.ease_step or 0) >= 3 else "learning"
        else:
            wrong_ids.append(w.id)
            step, interval, nxt = schedule_wrong(today)
            prog.ease_step = step
            prog.interval_days = interval
            prog.next_review_date = nxt
            prog.wrong_count = (prog.wrong_count or 0) + 1
            prog.last_result = "wrong"
            prog.status = "hard"
        details.append({"word_id": w.id, "word": w.word, "correct": is_ok, "expected": w.meaning})

    total = len(pack)
    all_correct = total > 0 and correct_n == total
    reward = _get_or_create_reward(db, user.id)
    stars = 0
    streak = reward.streak_days or 0

    log = db.scalar(
        select(VocabDailyLog).where(VocabDailyLog.user_id == user.id, VocabDailyLog.day == today_s)
    )
    if not log:
        log = VocabDailyLog(user_id=user.id, day=today_s, bank=prefs.bank)
        db.add(log)

    new_n = sum(1 for w in pack if w.role == "new")
    rev_n = total - new_n
    log.new_count = new_n
    log.review_count = rev_n
    log.quiz_total = total
    log.quiz_correct = correct_n
    log.bank = prefs.bank

    if all_correct and not log.completed:
        # 连续打卡
        yesterday = (today - timedelta(days=1)).isoformat()
        if reward.last_checkin_date == yesterday:
            streak = streak + 1
        elif reward.last_checkin_date == today_s:
            streak = max(streak, 1)
        else:
            streak = 1
        stars = star_for_streak(streak)
        reward.streak_days = streak
        reward.last_checkin_date = today_s
        reward.stars_total = (reward.stars_total or 0) + stars
        reward.stars_month = (reward.stars_month or 0) + stars
        log.stars_earned = stars
        log.completed = True
    elif not all_correct:
        # 未全对：不算打卡完成，但可保留进度；断签逻辑在下次全对时按日期判断
        log.completed = False
        log.stars_earned = 0

    db.commit()
    return {
        "total": total,
        "correct": correct_n,
        "wrong_ids": wrong_ids,
        "all_correct": all_correct,
        "stars_earned": stars,
        "streak_days": reward.streak_days,
        "stars_total": reward.stars_total,
        "stars_month": reward.stars_month,
        "details": details,
        "message": (
            f"全部正确！获得 {stars} 颗星，连续打卡 {reward.streak_days} 天"
            if all_correct
            else f"答对 {correct_n}/{total}，错题已纳入优先复习"
        ),
    }


@router.post("/course/redeem")
def redeem_membership(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    reward = _get_or_create_reward(db, user.id)
    if (reward.stars_month or 0) < STARS_PER_MONTH_MEMBER:
        raise HTTPException(
            status_code=400,
            detail=f"本月还需 {STARS_PER_MONTH_MEMBER - (reward.stars_month or 0)} 颗星才能兑换",
        )
    plan = db.scalar(select(MembershipPlan).order_by(MembershipPlan.days.desc(), MembershipPlan.id))
    if not plan:
        plan = MembershipPlan(name="月度会员（背单词兑换）", price=0, days=30, benefits="背单词星级兑换")
        db.add(plan)
        db.flush()
    order = Order(user_id=user.id, plan_id=plan.id, amount=0, status="paid")
    db.add(order)
    reward.stars_month -= STARS_PER_MONTH_MEMBER
    reward.redeemed_months = (reward.redeemed_months or 0) + 1
    db.commit()
    return {
        "status": "ok",
        "order_id": order.id,
        "plan": plan.name,
        "days": plan.days,
        "stars_month": reward.stars_month,
        "message": "已兑换一个月会员",
    }


@router.get("/admin", response_model=List[WordOut])
def admin_list(_: User = Depends(require_staff), db: Session = Depends(get_db)) -> List[WordOut]:
    return [_out(w) for w in db.scalars(select(VocabWord).order_by(VocabWord.id.desc()).limit(200))]


@router.post("/admin", response_model=WordOut)
def admin_create(
    body: WordIn,
    _: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> WordOut:
    data = body.model_dump()
    if not data.get("morphology_json"):
        data["morphology_json"] = morph_json_dumps(morph_for(body.word))
    if not data.get("image_key"):
        data["image_key"] = body.word.lower()
    w = VocabWord(**data)
    db.add(w)
    db.commit()
    db.refresh(w)
    return _out(w)


def seed_zhongkao_bank(db: Session) -> int:
    """幂等导入中考 800 词，并按 JSON 顺序写入 sort_order；示范词移出本词库。"""
    candidates = [
        Path(__file__).resolve().parents[1] / "data" / "vocab_zhongkao_800.json",  # app/data
        Path(__file__).resolve().parents[2] / "data" / "vocab_zhongkao_800.json",  # apps/api/data
    ]
    path = next((p for p in candidates if p.exists()), None)
    if not path:
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    official = {str(item["word"]).lower(): idx for idx, item in enumerate(data)}

    # 历史 seed 示范词若混入中考库且不在官方词表，移到 demo，避免打乱考试分类出题
    moved = 0
    for w in db.scalars(select(VocabWord).where(VocabWord.bank == "zhongkao_800")):
        key = (w.word or "").lower()
        if key and key not in official:
            w.bank = "demo"
            moved += 1

    by_word = {
        (w.word or "").lower(): w
        for w in db.scalars(select(VocabWord).where(VocabWord.bank == "zhongkao_800"))
    }
    added = 0
    updated = 0
    for idx, item in enumerate(data):
        key = str(item["word"]).lower()
        row = by_word.get(key)
        if row:
            if int(row.sort_order or 0) != idx or (row.frequency or "") != (item.get("frequency") or ""):
                row.sort_order = idx
                row.frequency = item.get("frequency") or row.frequency or ""
                row.scene = item.get("scene") or row.scene or ""
                row.pos = item.get("pos") or row.pos or ""
                if item.get("meanings") and not (row.meanings_json or "").strip():
                    row.meanings_json = json.dumps(item.get("meanings") or [], ensure_ascii=False)
                updated += 1
            continue
        morph = morph_for(item["word"])
        db.add(
            VocabWord(
                word=item["word"],
                phonetic=item.get("phonetic") or "",
                meaning=item.get("meaning") or "",
                example=item.get("example") or "",
                level=item.get("level") or "A2",
                bank="zhongkao_800",
                sort_order=idx,
                pos=item.get("pos") or "",
                scene=item.get("scene") or "",
                frequency=item.get("frequency") or "",
                meanings_json=json.dumps(item.get("meanings") or [], ensure_ascii=False),
                morphology_json=morph_json_dumps(morph),
                image_key=(item["word"] or "").lower(),
            )
        )
        added += 1
    if added or updated or moved:
        db.commit()
    return added
