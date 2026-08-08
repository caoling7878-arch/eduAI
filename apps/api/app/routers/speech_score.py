from __future__ import annotations

import re
from typing import List

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/speech", tags=["speech"])


class ScoreIn(BaseModel):
    expected: str = Field(min_length=1, max_length=2000)
    transcript: str = Field(min_length=0, max_length=2000)


class ScoreOut(BaseModel):
    score: int
    level: str
    matched: List[str]
    missing: List[str]
    feedback: str


def _words(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z']+", (text or "").lower())


@router.post("/score", response_model=ScoreOut)
def score_speech(body: ScoreIn) -> ScoreOut:
    """基于识别文本与目标句的词重叠，给出简易发音/表达评分（0-100）。"""
    exp = _words(body.expected)
    got = _words(body.transcript)
    if not exp:
        return ScoreOut(score=0, level="N/A", matched=[], missing=[], feedback="目标句为空")
    if not got:
        return ScoreOut(
            score=0,
            level="Beginner",
            matched=[],
            missing=exp[:8],
            feedback="未识别到有效英文单词，请靠近麦克风重试。",
        )

    exp_set = set(exp)
    got_set = set(got)
    matched = sorted(exp_set & got_set)
    missing = sorted(exp_set - got_set)
    # 覆盖率 + 长度惩罚
    cover = len(matched) / max(1, len(exp_set))
    length_ratio = min(1.0, len(got) / max(1, len(exp)))
    score = int(round((cover * 0.75 + length_ratio * 0.25) * 100))
    score = max(0, min(100, score))

    if score >= 85:
        level, tip = "Excellent", "表达很接近目标句，继续保持流利度。"
    elif score >= 70:
        level, tip = "Good", "大意正确，可补上缺失关键词让句子更完整。"
    elif score >= 50:
        level, tip = "Fair", "能听懂部分，建议跟读目标句 2 遍再试。"
    else:
        level, tip = "Needs work", "先慢速跟读目标句，注意关键词重音。"

    if missing:
        tip += f" 可重点练习：{', '.join(missing[:5])}."

    return ScoreOut(score=score, level=level, matched=matched[:12], missing=missing[:12], feedback=tip)
