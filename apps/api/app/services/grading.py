from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session

from ..models import GradeTask, Question, User
from .billing import check_quota
from .llm import chat_completion, get_active_prompt, get_default_provider, log_usage

DEFAULT_GRADE_PROMPT = (
    "你是严谨的学科阅卷老师。根据题干、参考答案/评分标准与学生作答，给出 JSON："
    '{"score": number, "confidence": 0到1小数, "feedback": "中文评语"}。'
    "只输出 JSON，不要其他文字。score 不得超过满分。"
)


def local_grade(question: Question, answer: str, max_score: float) -> Dict[str, Any]:
    ref = (question.answer or "").strip()
    text = (answer or "").strip()
    if not text:
        return {"score": 0.0, "confidence": 0.9, "feedback": "未作答，记 0 分。"}
    score = max_score * 0.4
    feedback = "【本地规则初评】已作答但未调用大模型。"
    if ref:
        # 关键词覆盖率粗评
        keys = [k for k in re.split(r"[,，、；;\s]+", ref) if len(k) >= 2]
        if keys:
            hit = sum(1 for k in keys if k.lower() in text.lower())
            ratio = hit / len(keys)
            score = round(max_score * min(1.0, 0.35 + ratio * 0.65), 1)
            feedback = f"【本地规则初评】命中参考要点 {hit}/{len(keys)}。建议教师复核。"
        elif ref.lower() in text.lower():
            score = round(max_score * 0.85, 1)
            feedback = "【本地规则初评】作答包含参考要点，建议教师复核确认。"
    if question.analysis:
        feedback += f" 评分参考：{question.analysis[:120]}"
    return {"score": score, "confidence": 0.45, "feedback": feedback}


def _parse_grade_json(raw: str, max_score: float) -> Optional[Dict[str, Any]]:
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        # 容错：截取首个 JSON 对象
        m = re.search(r"\{[\s\S]*\}", raw)
        obj = json.loads(m.group(0) if m else raw)
        score = float(obj.get("score", 0))
        score = max(0.0, min(max_score, score))
        conf = float(obj.get("confidence", 0.6))
        conf = max(0.0, min(1.0, conf))
        feedback = str(obj.get("feedback") or "").strip() or "已完成 AI 初评。"
        return {"score": score, "confidence": conf, "feedback": feedback}
    except Exception:  # noqa: BLE001
        return None


async def ai_grade_task(
    db: Session,
    task: GradeTask,
    question: Question,
    user: Optional[User] = None,
) -> GradeTask:
    max_score = float(task.max_score or 10)
    provider = get_default_provider(db)
    result: Optional[Dict[str, Any]] = None
    model_name = "local-grade"
    t0 = time.time()
    err = ""

    ok, quota_msg, _ = check_quota(db, user)
    if not ok and provider and provider.api_key:
        # 配额不足时降级本地规则，不阻断批改队列
        err = quota_msg
        provider = None

    if provider and provider.api_key and provider.base_url:
        system = get_active_prompt(db, "grade_rubric", DEFAULT_GRADE_PROMPT)
        user_prompt = (
            f"满分：{max_score}\n"
            f"题型：{question.type}\n"
            f"题干：{question.stem}\n"
            f"参考答案：{question.answer or '（无）'}\n"
            f"评分标准：{question.analysis or '按要点给分，表达清晰加分'}\n"
            f"学生作答：{task.answer_text}\n"
        )
        candidates = []
        for m in (provider.default_model, "gpt-4o-mini"):
            if m and m not in candidates:
                candidates.append(m)
        for model_name in candidates:
            try:
                raw = await chat_completion(
                    base_url=provider.base_url,
                    api_key=provider.api_key,
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.2,
                )
                result = _parse_grade_json(raw, max_score)
                if result:
                    break
                err = f"无法解析模型输出：{raw[:160]}"
            except Exception as e:  # noqa: BLE001
                err = str(e)
                result = None

    if result is None:
        result = local_grade(question, task.answer_text, max_score)
        model_name = "local-grade"

    task.ai_score = float(result["score"])
    task.ai_feedback = str(result["feedback"])
    task.ai_confidence = float(result["confidence"])
    task.status = "ai_scored"
    db.commit()
    db.refresh(task)

    log_usage(
        db,
        user=user,
        provider_id=provider.id if provider else None,
        model=model_name,
        purpose="grade",
        prompt_tokens=max(1, len(task.answer_text) // 4),
        completion_tokens=max(1, len(task.ai_feedback) // 4),
        latency_ms=int((time.time() - t0) * 1000),
        success=not bool(err) or model_name == "local-grade",
        error=err,
    )
    return task


def final_score(task: GradeTask) -> Tuple[Optional[float], str]:
    if task.status == "teacher_reviewed" and task.teacher_score is not None:
        return task.teacher_score, task.teacher_feedback or task.ai_feedback
    if task.ai_score is not None:
        return task.ai_score, task.ai_feedback
    return None, ""
