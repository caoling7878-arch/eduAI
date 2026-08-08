from __future__ import annotations

"""艾宾浩斯间隔与背单词日程辅助。"""

from datetime import date, timedelta
from typing import List, Tuple

# 复习间隔（天）：首次学完次日复习，再 2/4/7/15/30
EBBINGHAUS_INTERVALS = [1, 2, 4, 7, 15, 30]


def tomorrow(d: date | None = None) -> str:
    base = d or date.today()
    return (base + timedelta(days=1)).isoformat()


def add_days(d: date, n: int) -> str:
    return (d + timedelta(days=n)).isoformat()


def next_interval(step: int) -> Tuple[int, int]:
    """返回 (new_step, interval_days)。"""
    if step < 0:
        step = 0
    if step >= len(EBBINGHAUS_INTERVALS):
        return len(EBBINGHAUS_INTERVALS) - 1, EBBINGHAUS_INTERVALS[-1]
    return step, EBBINGHAUS_INTERVALS[step]


def schedule_ok(ease_step: int, today: date | None = None) -> Tuple[int, int, str]:
    """答对后推进间隔。ease_step 为当前已完成的档位，取对应间隔后 +1。"""
    base = today or date.today()
    idx = min(max(ease_step, 0), len(EBBINGHAUS_INTERVALS) - 1)
    interval = EBBINGHAUS_INTERVALS[idx]
    new_step = min(ease_step + 1, len(EBBINGHAUS_INTERVALS) - 1)
    return new_step, interval, add_days(base, interval)


def schedule_wrong(today: date | None = None) -> Tuple[int, int, str]:
    """答错：重置，次日优先复习。"""
    base = today or date.today()
    return 0, 1, add_days(base, 1)


def star_for_streak(streak_days: int) -> int:
    """连续打卡 ≥10 天每天 2 星，否则 1 星。断签后由调用方把 streak 置 1。"""
    return 2 if streak_days >= 10 else 1
