from __future__ import annotations

import json
import re
import time
from typing import Any, AsyncIterator, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit_util import write_audit
from ..auth import get_current_user, get_optional_user
from ..db import SessionLocal, get_db
from ..models import LabPage, LabPageQuestion, Lesson, Question, User, WrongItem
from ..rbac import require_staff
from ..services.billing import check_quota
from ..services.llm import chat_completion, get_default_provider, log_usage, stream_chat_completion

router = APIRouter(prefix="/labs", tags=["labs"])

_KEYWORD_MAP = [
    (("正方体", "立方体"), "cube", "立体几何"),
    (("长方体",), "box", "立体几何"),
    (("棱锥", "四棱锥", "三棱锥"), "pyramid", "立体几何"),
    (("随机", "变式"), "random-7", "立体几何"),
    (("椭圆",), "ellipse_dot_range", "解析几何"),
    (("抛物线",), "parabola_dot_const", "解析几何"),
    (("双曲线", "离心率"), "hyperbola_ecc_range", "解析几何"),
    (("甲烷", "燃烧", "CH4", "ch4"), "combustion_ch4", "化学反应"),
    (("酯化", "乙酸", "乙醇"), "esterification", "化学反应"),
]


class LabOut(BaseModel):
    id: int
    page_key: str
    title: str
    category: str
    description: str
    preview_path: str
    knowledge_points: str = ""
    question_ids: List[int] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class LabPatch(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    knowledge_points: Optional[str] = None
    category: Optional[str] = None
    question_ids: Optional[List[int]] = None


class AttachIn(BaseModel):
    lesson_id: int
    page_key: str
    title: Optional[str] = None


class VisionReadIn(BaseModel):
    text: str = ""
    image_base64: str = ""
    mime: str = "image/jpeg"


class PracticeCheckIn(BaseModel):
    question_id: int
    answer: str = Field(min_length=0, max_length=500)


class GeometryChatTurn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=4000)


class GeometryTutorIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: List[GeometryChatTurn] = Field(default_factory=list, max_length=20)
    image_base64: str = ""
    mime: str = "image/jpeg"


_GEOMETRY_TUTOR_SYSTEM = (
    "你是 eduAI 几何动图实验室的讲解助教，擅长立体几何、解析几何与化学微观动图。"
    "用户会用自然语言描述题目或追问。请用分步、易懂的中文讲解思路，可用 Markdown。"
    "讲解时：先概括题意 → 给出关键辅助线/建系思路 → 分步推导 → 提示可用交互课页验证。"
    "若用户追问，结合上下文继续，不要重复整段开场白。鼓励打开对应动图课页动手验证。"
)


def _parse_ids(raw: str) -> List[int]:
    out: List[int] = []
    for part in (raw or "").split(","):
        part = part.strip()
        if part.isdigit():
            out.append(int(part))
    return out


def _lab_out(db: Session, page: LabPage) -> LabOut:
    linked = list(db.scalars(select(LabPageQuestion.question_id).where(LabPageQuestion.page_key == page.page_key)))
    ids = linked or _parse_ids(page.question_ids or "")
    return LabOut(
        id=page.id,
        page_key=page.page_key,
        title=page.title,
        category=page.category,
        description=page.description,
        preview_path=page.preview_path,
        knowledge_points=page.knowledge_points or "",
        question_ids=ids,
    )


def _sync_lab_links(db: Session, page_key: str, question_ids: List[int]) -> None:
    for row in list(db.scalars(select(LabPageQuestion).where(LabPageQuestion.page_key == page_key))):
        db.delete(row)
    for i, qid in enumerate(question_ids):
        if db.get(Question, qid):
            db.add(LabPageQuestion(page_key=page_key, question_id=qid, sort_order=i))


def _question_public(q: Question, reason: str = "") -> dict:
    try:
        options = json.loads(q.options_json or "[]")
    except json.JSONDecodeError:
        options = []
    return {
        "id": q.id,
        "type": q.type,
        "stem": q.stem,
        "options": options,
        "knowledge_points": q.knowledge_points,
        "difficulty": q.difficulty,
        "reason": reason,
    }


def _pick_questions(
    db: Session,
    kps: List[str],
    limit: int,
    reason_prefix: str,
    *,
    explicit_ids: Optional[List[int]] = None,
    exclude_ids: Optional[set[int]] = None,
    variant: bool = False,
    seed: int = 0,
) -> List[dict]:
    questions: List[dict] = []
    seen: set[int] = set(exclude_ids or set())

    if explicit_ids:
        for qid in explicit_ids:
            if qid in seen:
                continue
            q = db.get(Question, qid)
            if not q or q.type == "essay":
                continue
            seen.add(qid)
            questions.append(_question_public(q, f"{reason_prefix} · 显式关联"))
            if len(questions) >= limit:
                return questions

    pool: List[Question] = []
    for kp in kps or ["立体几何"]:
        rows = list(
            db.scalars(
                select(Question)
                .where(Question.knowledge_points.contains(kp), Question.type != "essay")
                .order_by(Question.difficulty, Question.id)
                .limit(limit * 3)
            )
        )
        pool.extend(rows)

    if variant and pool:
        # 伪随机变式：按 seed 打乱，保证同 seed 可复现
        rng = __import__("random").Random(seed or 7)
        pool = list({q.id: q for q in pool}.values())
        rng.shuffle(pool)
        # 变式优先不同难度组合
        pool.sort(key=lambda q: (q.difficulty + (q.id % 3), q.id))

    for q in pool:
        if q.id in seen:
            continue
        seen.add(q.id)
        label = "变式巩固" if variant else reason_prefix
        questions.append(_question_public(q, f"{label} · {q.knowledge_points or '综合'}"))
        if len(questions) >= limit:
            break
    return questions


def _heuristic_from_text(text: str) -> dict:
    hits = []
    for keys, page_key, kp in _KEYWORD_MAP:
        if any(k.lower() in text.lower() for k in keys):
            hits.append({"page_key": page_key, "knowledge_point": kp})
    # 去重保序
    seen = set()
    labs = []
    kps = []
    for h in hits:
        if h["page_key"] not in seen:
            seen.add(h["page_key"])
            labs.append(h["page_key"])
            if h["knowledge_point"] not in kps:
                kps.append(h["knowledge_point"])
    if not labs:
        labs = ["cube"]
        kps = ["立体几何"]
    return {
        "stem": text.strip() or "（未识别到清晰题干，已按常见立体几何推荐）",
        "knowledge_points": kps,
        "suggested_labs": labs,
        "source": "heuristic",
    }


@router.get("/pages", response_model=List[LabOut])
def list_pages(db: Session = Depends(get_db)) -> List[LabOut]:
    return [_lab_out(db, p) for p in db.scalars(select(LabPage).order_by(LabPage.category, LabPage.id))]


@router.get("/pages/{page_key}", response_model=LabOut)
def get_page(page_key: str, db: Session = Depends(get_db)) -> LabOut:
    page = db.scalar(select(LabPage).where(LabPage.page_key == page_key))
    if not page:
        raise HTTPException(status_code=404, detail="课页不存在")
    return _lab_out(db, page)


@router.patch("/pages/{page_key}", response_model=LabOut)
def patch_page(
    page_key: str,
    body: LabPatch,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> LabOut:
    page = db.scalar(select(LabPage).where(LabPage.page_key == page_key))
    if not page:
        raise HTTPException(status_code=404, detail="课页不存在")
    data = body.model_dump(exclude_unset=True)
    qids = data.pop("question_ids", None)
    for k, v in data.items():
        setattr(page, k, v)
    if qids is not None:
        page.question_ids = ",".join(str(i) for i in qids)
        _sync_lab_links(db, page.page_key, qids)
    write_audit(db, user=admin, action="lab.patch", resource=page_key)
    db.commit()
    db.refresh(page)
    return _lab_out(db, page)


@router.get("/pages/{page_key}/practice")
def lab_practice(
    page_key: str,
    limit: int = 6,
    seed: int = 0,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
) -> dict:
    """学完课页后，按显式关联/知识点推荐客观题；random-7 走可复现变式。"""
    page = db.scalar(select(LabPage).where(LabPage.page_key == page_key))
    if not page:
        raise HTTPException(status_code=404, detail="课页不存在")
    kps = [p.strip() for p in (page.knowledge_points or "").split(",") if p.strip()]
    linked = list(
        db.scalars(
            select(LabPageQuestion.question_id)
            .where(LabPageQuestion.page_key == page_key)
            .order_by(LabPageQuestion.sort_order, LabPageQuestion.id)
        )
    )
    explicit = linked or _parse_ids(page.question_ids or "")
    exclude: set[int] = set()
    if user:
        mastered = list(
            db.scalars(
                select(WrongItem.question_id).where(
                    WrongItem.user_id == user.id, WrongItem.mastered.is_(True)
                )
            )
        )
        exclude.update(mastered)
    variant = page.page_key == "random-7" or "变式" in (page.title or "")
    questions = _pick_questions(
        db,
        kps or ["立体几何"],
        limit,
        f"课页「{page.title}」关联",
        explicit_ids=None if variant else explicit,
        exclude_ids=exclude,
        variant=variant,
        seed=seed or (hash(page_key) % 10_000),
    )
    # 变式页：若有显式关联，优先作为候选池再洗牌
    if variant and explicit and len(questions) < limit:
        extra = _pick_questions(
            db,
            kps or ["立体几何"],
            limit,
            f"课页「{page.title}」变式",
            explicit_ids=explicit,
            exclude_ids={q["id"] for q in questions} | exclude,
            variant=True,
            seed=(seed or 7) + 1,
        )
        questions = (questions + extra)[:limit]
    return {
        "page_key": page.page_key,
        "title": page.title,
        "knowledge_points": kps,
        "mode": "variant" if variant else "related",
        "linked_question_ids": explicit,
        "questions": questions,
    }


@router.post("/practice/check")
def practice_check(
    body: PracticeCheckIn,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
) -> dict:
    q = db.get(Question, body.question_id)
    if not q or q.type == "essay":
        raise HTTPException(status_code=404, detail="题目不存在")
    raw = (body.answer or "").strip()
    expected = (q.answer or "").strip()
    correct = False
    if q.type in ("single", "judge"):
        correct = raw == expected
    else:
        # 填空：允许逗号分隔顺序一致或去空格比较
        def norm(s: str) -> str:
            return re.sub(r"\s+", "", s.replace("，", ","))

        correct = norm(raw) == norm(expected) or norm(raw).lower() == norm(expected).lower()

    synced = False
    if user:
        existing = db.scalar(
            select(WrongItem).where(WrongItem.user_id == user.id, WrongItem.question_id == q.id)
        )
        if correct:
            if existing:
                existing.mastered = True
                synced = True
        else:
            if existing:
                existing.mastered = False
                existing.user_answer = raw
                existing.correct_answer = expected
                existing.knowledge_points = q.knowledge_points or ""
                existing.source = "practice"
            else:
                db.add(
                    WrongItem(
                        user_id=user.id,
                        question_id=q.id,
                        user_answer=raw,
                        correct_answer=expected,
                        knowledge_points=q.knowledge_points or "",
                        source="practice",
                        mastered=False,
                    )
                )
            synced = True
        db.commit()

    return {
        "question_id": q.id,
        "correct": correct,
        "expected": expected if not correct else None,
        "analysis": q.analysis if not correct else (q.analysis or "回答正确"),
        "synced_wrongbook": synced,
    }


@router.post("/vision-read")
async def vision_read(
    body: VisionReadIn,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
) -> dict:
    """图片/文字读题：识别题干与知识点，推荐课页与巩固题。无视觉模型时回退关键词启发式。"""
    text = (body.text or "").strip()
    image_b64 = (body.image_base64 or "").strip()
    if image_b64.startswith("data:"):
        # data URL
        try:
            header, image_b64 = image_b64.split(",", 1)
            if ":" in header and ";" in header:
                body.mime = header.split(":")[1].split(";")[0] or body.mime
        except ValueError:
            pass

    if not text and not image_b64:
        raise HTTPException(status_code=400, detail="请上传题目图片或粘贴题干文字")

    parsed: Dict[str, Any]
    provider = get_default_provider(db)

    if provider and provider.api_key and (image_b64 or text):
        content: Any
        if image_b64:
            content = [
                {
                    "type": "text",
                    "text": (
                        "你是高中数理化助教。请从题目图片中提取题干，并判断最相关的知识点。"
                        "只返回 JSON：{\"stem\":\"题干\",\"knowledge_points\":[\"知识点\"],\"hint\":\"一句话提示\"}。"
                        "知识点优先从：立体几何、线面关系、解析几何、化学反应 中选择。"
                        + (f" 用户补充文字：{text}" if text else "")
                    ),
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{body.mime};base64,{image_b64}"},
                },
            ]
        else:
            content = (
                "从下面题目文字提取题干与知识点，只返回 JSON："
                '{"stem":"...","knowledge_points":["..."],"hint":"..."}。'
                f"题目：{text}"
            )
        messages = [
            {"role": "system", "content": "你只输出合法 JSON，不要 Markdown。"},
            {"role": "user", "content": content},
        ]
        try:
            import time

            t0 = time.time()
            raw = await chat_completion(
                base_url=provider.base_url,
                api_key=provider.api_key,
                model=provider.default_model or "gpt-4o-mini",
                messages=messages,
                temperature=0.2,
                max_tokens=600,
            )
            latency = int((time.time() - t0) * 1000)
            log_usage(
                db,
                user=user,
                provider_id=provider.id,
                model=provider.default_model or "",
                purpose="vision_read",
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=latency,
                success=True,
            )
            m = re.search(r"\{[\s\S]*\}", raw)
            data = json.loads(m.group(0) if m else raw)
            stem = str(data.get("stem") or text or "").strip()
            kps = data.get("knowledge_points") or []
            if isinstance(kps, str):
                kps = [kps]
            kps = [str(k).strip() for k in kps if str(k).strip()]
            hint = str(data.get("hint") or "")
            # 用 stem 再做一次课页映射
            mapped = _heuristic_from_text(stem + " " + " ".join(kps))
            parsed = {
                "stem": stem or mapped["stem"],
                "knowledge_points": kps or mapped["knowledge_points"],
                "suggested_labs": mapped["suggested_labs"],
                "hint": hint,
                "source": "llm",
            }
        except Exception as e:
            log_usage(
                db,
                user=user,
                provider_id=provider.id if provider else None,
                model=(provider.default_model if provider else "") or "",
                purpose="vision_read",
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=0,
                success=False,
                error=str(e),
            )
            parsed = _heuristic_from_text(text or "立体几何")
            parsed["hint"] = "视觉模型暂不可用，已按关键词推荐（可补充题干文字提高精度）。"
            parsed["llm_error"] = str(e)[:160]
    else:
        parsed = _heuristic_from_text(text or "立体几何")
        if image_b64 and not text:
            parsed["hint"] = "未配置可用大模型时，图片读题会降级；请粘贴题干文字以获得更准推荐。"
        else:
            parsed["hint"] = "已按关键词匹配课页与巩固题。"

    # 绑定真实课页元数据
    lab_rows = []
    for key in parsed["suggested_labs"]:
        page = db.scalar(select(LabPage).where(LabPage.page_key == key))
        if page:
            lab_rows.append(
                {
                    "page_key": page.page_key,
                    "title": page.title,
                    "category": page.category,
                    "preview_path": page.preview_path,
                    "knowledge_points": page.knowledge_points,
                }
            )
    questions = _pick_questions(db, parsed["knowledge_points"], 5, "读题推荐")
    return {
        "stem": parsed["stem"],
        "knowledge_points": parsed["knowledge_points"],
        "suggested_labs": lab_rows,
        "questions": questions,
        "source": parsed.get("source", "heuristic"),
        "hint": parsed.get("hint", ""),
    }


def _lab_rows_for_keys(db: Session, keys: List[str]) -> List[dict]:
    rows = []
    seen: set[str] = set()
    for key in keys:
        if key in seen:
            continue
        page = db.scalar(select(LabPage).where(LabPage.page_key == key))
        if page:
            seen.add(key)
            rows.append(
                {
                    "page_key": page.page_key,
                    "title": page.title,
                    "category": page.category,
                    "preview_path": page.preview_path,
                    "knowledge_points": page.knowledge_points,
                }
            )
    return rows


def _extract_steps(text: str) -> List[str]:
    steps: List[str] = []
    for line in (text or "").splitlines():
        m = re.match(r"^\s*(?:\d+[\.\)、]|[-*])\s*(.+)", line.strip())
        if m:
            step = m.group(1).strip()
            if len(step) >= 4:
                steps.append(step)
    return steps[:8]


def _heuristic_geometry_reply(user_text: str, db: Session) -> dict:
    mapped = _heuristic_from_text(user_text)
    labs = _lab_rows_for_keys(db, mapped["suggested_labs"])
    kps = mapped["knowledge_points"]
    topic = user_text.strip()[:80] or "这道几何题"
    steps = [
        "读题：圈出已知条件、所求量与图形关系",
        "建模：选择建系、作辅助线或参数化关键量",
        "推导：用向量/距离/角度公式分步计算",
        "验证：打开下方推荐动图课页，拖动滑块对照结果",
    ]
    if any(k in user_text for k in ("正方体", "立方体", "线面角")):
        steps[1] = "建系：以底面顶点为原点，棱为坐标轴（见「正方体·线面角」课页）"
    elif any(k in user_text for k in ("椭圆", "焦点", "离心率")):
        steps[1] = "设椭圆标准方程 x²/a² + y²/b² = 1，用焦点/离心率条件列方程"
    lab_hint = labs[0]["title"] if labs else "正方体 · 线面角"
    reply = (
        f"针对「{topic}」，建议按以下思路分析：\n\n"
        + "\n".join(f"{i + 1}. {s}" for i, s in enumerate(steps))
        + f"\n\n**推荐交互课页**：{lab_hint} —— 拖动模型可直观看到线面角、体积或曲线变化。"
        + "\n\n（当前未接入大模型，以上为关键词匹配的讲解模板；配置 LLM 后可获得更细的逐步推导。）"
    )
    return {
        "reply": reply,
        "steps": steps,
        "knowledge_points": kps,
        "suggested_labs": labs,
        "source": "heuristic",
    }


def _geometry_meta_from_text(db: Session, text: str) -> dict:
    mapped = _heuristic_from_text(text)
    labs = _lab_rows_for_keys(db, mapped["suggested_labs"])
    return {
        "knowledge_points": mapped["knowledge_points"],
        "suggested_labs": labs,
    }


@router.post("/geometry-tutor/stream")
async def geometry_tutor_stream(
    body: GeometryTutorIn,
    user: Optional[User] = Depends(get_optional_user),
) -> StreamingResponse:
    """对话式几何讲解：SSE 流式输出讲解，末尾附带推荐课页与步骤。"""

    async def gen() -> AsyncIterator[str]:
        db = SessionLocal()
        t0 = time.time()
        provider_id = None
        model_name = "heuristic"
        user_text = body.message.strip()
        try:
            if user:
                ok, quota_msg, _ = check_quota(db, user)
                if not ok:
                    yield f"data: {json.dumps({'type': 'error', 'message': quota_msg, 'code': 'quota_exceeded'}, ensure_ascii=False)}\n\n"
                    yield "data: [DONE]\n\n"
                    return

            image_b64 = (body.image_base64 or "").strip()
            if image_b64.startswith("data:"):
                try:
                    header, image_b64 = image_b64.split(",", 1)
                    if ":" in header and ";" in header:
                        body.mime = header.split(":")[1].split(";")[0] or body.mime
                except ValueError:
                    pass

            provider = get_default_provider(db)
            full: List[str] = []
            source = "heuristic"

            if provider and provider.api_key and provider.base_url:
                messages: List[Dict[str, Any]] = [{"role": "system", "content": _GEOMETRY_TUTOR_SYSTEM}]
                for turn in body.history[-12:]:
                    messages.append({"role": turn.role, "content": turn.content.strip()})
                if image_b64:
                    user_content: Any = [
                        {
                            "type": "text",
                            "text": (
                                user_text
                                or "请根据题目图片分步讲解思路，并说明适合打开哪类交互课页验证。"
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{body.mime};base64,{image_b64}"},
                        },
                    ]
                else:
                    user_content = user_text
                messages.append({"role": "user", "content": user_content})

                provider_id = provider.id
                model_name = provider.default_model or "gpt-4o-mini"
                try:
                    async for delta in stream_chat_completion(
                        base_url=provider.base_url,
                        api_key=provider.api_key,
                        model=model_name,
                        messages=messages,
                        temperature=0.35,
                    ):
                        full.append(delta)
                        yield f"data: {json.dumps({'type': 'delta', 'content': delta}, ensure_ascii=False)}\n\n"
                    source = "llm"
                    est_p = max(1, len(json.dumps(messages, ensure_ascii=False)) // 4)
                    est_c = max(1, len("".join(full)) // 4)
                    log_usage(
                        db,
                        user=user,
                        provider_id=provider_id,
                        model=model_name,
                        purpose="geometry_tutor",
                        prompt_tokens=est_p,
                        completion_tokens=est_c,
                        latency_ms=int((time.time() - t0) * 1000),
                        success=True,
                    )
                except Exception as e:  # noqa: BLE001
                    log_usage(
                        db,
                        user=user,
                        provider_id=provider_id,
                        model=model_name,
                        purpose="geometry_tutor",
                        latency_ms=int((time.time() - t0) * 1000),
                        success=False,
                        error=str(e),
                    )
                    fallback = _heuristic_geometry_reply(user_text, db)
                    text = f"（模型暂不可用：{str(e)[:80]}）\n\n{fallback['reply']}"
                    full = [text]
                    source = "heuristic"
                    chunk = ""
                    for ch in text:
                        chunk += ch
                        if len(chunk) >= 12:
                            yield f"data: {json.dumps({'type': 'delta', 'content': chunk}, ensure_ascii=False)}\n\n"
                            chunk = ""
                    if chunk:
                        yield f"data: {json.dumps({'type': 'delta', 'content': chunk}, ensure_ascii=False)}\n\n"
            else:
                fallback = _heuristic_geometry_reply(user_text, db)
                text = fallback["reply"]
                if image_b64 and not user_text:
                    text = "已收到题目图片。未配置大模型时暂无法识图，请用文字描述题干，或前往「图片读题」页粘贴文字。\n\n" + text
                full = [text]
                chunk = ""
                for ch in text:
                    chunk += ch
                    if len(chunk) >= 12:
                        yield f"data: {json.dumps({'type': 'delta', 'content': chunk}, ensure_ascii=False)}\n\n"
                        chunk = ""
                if chunk:
                    yield f"data: {json.dumps({'type': 'delta', 'content': chunk}, ensure_ascii=False)}\n\n"

            answer = "".join(full)
            meta = _geometry_meta_from_text(db, user_text or answer)
            steps = _extract_steps(answer) or _heuristic_geometry_reply(user_text, db)["steps"]
            yield f"data: {json.dumps({'type': 'meta', 'source': source, 'steps': steps, 'knowledge_points': meta['knowledge_points'], 'suggested_labs': meta['suggested_labs']}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'content': answer}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:  # noqa: BLE001
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        finally:
            db.close()

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/attach")
def attach_to_lesson(
    body: AttachIn,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> dict:
    lesson = db.get(Lesson, body.lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="课时不存在")
    page = db.scalar(select(LabPage).where(LabPage.page_key == body.page_key))
    if not page:
        raise HTTPException(status_code=404, detail="课页不存在")
    lesson.content_type = "interactive_lab"
    lesson.content = page.page_key
    if body.title:
        lesson.title = body.title
    write_audit(db, user=admin, action="lab.attach", resource=f"{body.lesson_id}:{body.page_key}")
    db.commit()
    return {
        "status": "ok",
        "lesson_id": lesson.id,
        "page_key": page.page_key,
        "preview": f"/courses/geometry-lab/{page.page_key}",
    }
