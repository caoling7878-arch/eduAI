"""小学数学计算专项：题库主题、解析 PDF、规则生成与答案评判。"""

from __future__ import annotations

import ast
import operator
import random
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

GRADE_META = [
    {
        "grade": 1,
        "topic": "100以内的数比大小",
        "prompt_hint": "填 >、< 或 =",
        "answer_kind": "compare",
        "pdf_keywords": ["100以内的数比大小"],
    },
    {
        "grade": 2,
        "topic": "混合运算（二）",
        "prompt_hint": "按运算顺序计算",
        "answer_kind": "number",
        "pdf_keywords": ["混合运算"],
    },
    {
        "grade": 3,
        "topic": "乘法交换律和结合律",
        "prompt_hint": "计算得数",
        "answer_kind": "number",
        "pdf_keywords": ["乘法交换律", "结合律"],
    },
    {
        "grade": 4,
        "topic": "小数比大小",
        "prompt_hint": "填 >、< 或 =",
        "answer_kind": "compare",
        "pdf_keywords": ["小数比大小"],
    },
    {
        "grade": 5,
        "topic": "分数连乘",
        "prompt_hint": "结果写成分数（可约分）",
        "answer_kind": "fraction",
        "pdf_keywords": ["分数连乘"],
    },
    {
        "grade": 6,
        "topic": "异分母分数加减法",
        "prompt_hint": "结果写成分数（可约分）",
        "answer_kind": "fraction",
        "pdf_keywords": ["异分母分数"],
    },
]

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,
}


@dataclass
class RawItem:
    grade: int
    topic: str
    stem: str
    answer: str
    answer_kind: str
    source: str = "gen"  # gen|pdf


def meta_for(grade: int) -> dict:
    for m in GRADE_META:
        if m["grade"] == grade:
            return m
    raise ValueError(f"unsupported grade: {grade}")


def format_fraction(f: Fraction, *, mixed: bool = False) -> str:
    """格式化分数。题干默认用 a/b（分子/分母）；mixed=True 时可用带分数。"""
    f = Fraction(f).limit_denominator()
    if f.denominator == 1:
        return str(f.numerator)
    if mixed and abs(f.numerator) > f.denominator:
        whole = abs(f.numerator) // f.denominator
        rem = abs(f.numerator) % f.denominator
        sign = "-" if f.numerator < 0 else ""
        if rem == 0:
            return f"{sign}{whole}"
        return f"{sign}{whole}又{rem}/{f.denominator}"
    return f"{f.numerator}/{f.denominator}"


def stem_fraction(f: Fraction) -> str:
    """题干用：始终分子/分母，便于前端画分数线。"""
    return format_fraction(f, mixed=False)


def format_number(val) -> str:
    if isinstance(val, Fraction):
        return format_fraction(val)
    if isinstance(val, float):
        d = Decimal(str(val)).normalize()
        s = format(d, "f")
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return s or "0"
    if isinstance(val, Decimal):
        s = format(val.normalize(), "f")
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return s or "0"
    if isinstance(val, int):
        return str(val)
    return str(val)


def _eval_ast(node):
    if isinstance(node, ast.Expression):
        return _eval_ast(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return Fraction(node.value).limit_denominator() if isinstance(node.value, float) else Fraction(node.value)
    if isinstance(node, ast.Num):  # py<3.8 compat
        return Fraction(node.n)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_ast(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_ast(node.left), _eval_ast(node.right))
    raise ValueError("unsupported expression")


def eval_math_expr(expr: str) -> Fraction:
    s = (
        expr.strip()
        .replace("×", "*")
        .replace("÷", "/")
        .replace("＋", "+")
        .replace("－", "-")
        .replace("（", "(")
        .replace("）", ")")
        .replace(" ", "")
    )
    tree = ast.parse(s, mode="eval")
    return Fraction(_eval_ast(tree)).limit_denominator()


def normalize_answer(raw: str, kind: str) -> str:
    s = (raw or "").strip().replace(" ", "").replace("＞", ">").replace("＜", "<").replace("＝", "=")
    s = s.replace("大于", ">").replace("小于", "<").replace("等于", "=")
    if kind == "compare":
        if s in (">", "<", "="):
            return s
        return s
    s = s.replace("／", "/").replace(":", "/")
    # 带分数：3又1/4
    m = re.fullmatch(r"(-?)(\d+)又(\d+)/(\d+)", s)
    if m:
        sign, whole, num, den = m.groups()
        f = Fraction(int(whole)) + Fraction(int(num), int(den))
        if sign == "-":
            f = -f
        return format_fraction(f)
    if "/" in s and re.fullmatch(r"-?\d+/\d+", s):
        a, b = s.split("/", 1)
        return format_fraction(Fraction(int(a), int(b)))
    try:
        if "." in s:
            return format_number(Decimal(s))
        return format_fraction(Fraction(int(s)))
    except (ValueError, InvalidOperation, ZeroDivisionError):
        return s


def answers_equal(user: str, correct: str, kind: str) -> bool:
    u = normalize_answer(user, kind)
    c = normalize_answer(correct, kind)
    if kind == "compare":
        return u == c
    if u == c:
        return True

    def to_frac(x: str) -> Fraction:
        m = re.fullmatch(r"(-?)(\d+)又(\d+)/(\d+)", x)
        if m:
            sign, whole, num, den = m.groups()
            f = Fraction(int(whole)) + Fraction(int(num), int(den))
            return -f if sign == "-" else f
        if "/" in x and re.fullmatch(r"-?\d+/\d+", x):
            a, b = x.split("/", 1)
            return Fraction(int(a), int(b))
        return Fraction(Decimal(x))

    try:
        return to_frac(u) == to_frac(c)
    except Exception:
        return False


# ---------- generators ----------


def _gen_g1(n: int, rng: random.Random) -> List[RawItem]:
    out: List[RawItem] = []
    seen = set()
    while len(out) < n:
        a, b = rng.randint(1, 100), rng.randint(1, 100)
        key = (a, b)
        if key in seen:
            continue
        seen.add(key)
        ans = ">" if a > b else "<" if a < b else "="
        out.append(
            RawItem(1, "100以内的数比大小", f"{a} ○ {b}", ans, "compare", "gen")
        )
    return out


def _gen_g2(n: int, rng: random.Random) -> List[RawItem]:
    out: List[RawItem] = []
    for _ in range(n * 3):
        if len(out) >= n:
            break
        kind = rng.choice(["add_mul", "sub_mul", "add_div", "sub_div", "mul_add", "mul_sub"])
        try:
            if kind == "add_mul":
                a, b, c = rng.randint(1, 80), rng.randint(1, 9), rng.randint(1, 9)
                stem = f"{a} + {b} × {c} ="
                ans = a + b * c
            elif kind == "sub_mul":
                b, c = rng.randint(1, 9), rng.randint(1, 9)
                a = b * c + rng.randint(0, 40)
                stem = f"{a} - {b} × {c} ="
                ans = a - b * c
            elif kind == "add_div":
                b, c = rng.randint(1, 9), rng.randint(1, 9)
                prod = b * c
                a = rng.randint(1, 60)
                stem = f"{a} + {prod} ÷ {c} ="
                ans = a + prod // c
            elif kind == "sub_div":
                b, c = rng.randint(2, 9), rng.randint(1, 9)
                prod = b * c
                a = prod + rng.randint(0, 50)
                stem = f"{a} - {prod} ÷ {c} ="
                ans = a - prod // c
            elif kind == "mul_add":
                a, b, c = rng.randint(1, 9), rng.randint(1, 9), rng.randint(1, 60)
                stem = f"{a} × {b} + {c} ="
                ans = a * b + c
            else:
                a, b = rng.randint(2, 9), rng.randint(1, 9)
                c = rng.randint(0, a * b)
                stem = f"{a} × {b} - {c} ="
                ans = a * b - c
            if ans < 0:
                continue
            out.append(RawItem(2, "混合运算（二）", stem, str(ans), "number", "gen"))
        except Exception:
            continue
    return out[:n]


def _gen_g3(n: int, rng: random.Random) -> List[RawItem]:
    out: List[RawItem] = []
    nice = [4, 5, 8, 25, 125]
    while len(out) < n:
        if rng.random() < 0.7:
            a = rng.choice(nice)
            b = rng.randint(11, 99)
            c = rng.choice([4, 5, 8] if a in (25, 125) else nice)
            stem = f"{a} × {b} × {c} ="
            ans = a * b * c
        else:
            a = rng.choice([1000, 2000, 3000, 4000, 5000, 8000])
            b = rng.choice([4, 5, 8, 25, 125])
            c = rng.choice([4, 5, 8])
            if a % (b * c) != 0 and a % b != 0:
                continue
            stem = f"{a} ÷ {b} ÷ {c} ="
            try:
                ans = a // b // c
            except ZeroDivisionError:
                continue
        out.append(RawItem(3, "乘法交换律和结合律", stem, str(ans), "number", "gen"))
    return out


def _rand_decimal(rng: random.Random, places: int = 2) -> Decimal:
    whole = rng.randint(0, 99)
    frac = "".join(str(rng.randint(0, 9)) for _ in range(places))
    return Decimal(f"{whole}.{frac}")


def _gen_g4(n: int, rng: random.Random) -> List[RawItem]:
    out: List[RawItem] = []
    seen = set()
    while len(out) < n:
        a = _rand_decimal(rng, rng.choice([1, 2, 3]))
        b = _rand_decimal(rng, rng.choice([1, 2, 3]))
        if rng.random() < 0.15:
            b = a
        key = (str(a), str(b))
        if key in seen:
            continue
        seen.add(key)
        ans = ">" if a > b else "<" if a < b else "="
        out.append(RawItem(4, "小数比大小", f"{a} ○ {b}", ans, "compare", "gen"))
    return out


def _rand_frac(rng: random.Random, max_den: int = 12, *, proper: bool = True) -> Fraction:
    """生成分数；proper=True 时分子小于分母（教材常见真分数）。"""
    den = rng.randint(2, max_den)
    if proper:
        num = rng.randint(1, den - 1)
    else:
        num = rng.randint(1, den * 2)
    return Fraction(num, den)


def _gen_g5(n: int, rng: random.Random) -> List[RawItem]:
    out: List[RawItem] = []
    while len(out) < n:
        a, b, c = _rand_frac(rng), _rand_frac(rng), _rand_frac(rng, 9)
        stem = f"{stem_fraction(a)} × {stem_fraction(b)} × {stem_fraction(c)} ="
        ans = format_fraction(a * b * c)
        out.append(RawItem(5, "分数连乘", stem, ans, "fraction", "gen"))
    return out


def _gen_g6(n: int, rng: random.Random) -> List[RawItem]:
    """异分母分数加减法：保留题型，题干用分子/分母形式。"""
    out: List[RawItem] = []
    while len(out) < n:
        a, b = _rand_frac(rng, 24), _rand_frac(rng, 24)
        if a.denominator == b.denominator:
            continue
        if rng.random() < 0.5:
            if a < b:
                a, b = b, a
            stem = f"{stem_fraction(a)} - {stem_fraction(b)} ="
            ans = format_fraction(a - b)
        else:
            stem = f"{stem_fraction(a)} + {stem_fraction(b)} ="
            ans = format_fraction(a + b)
        out.append(RawItem(6, "异分母分数加减法", stem, ans, "fraction", "gen"))
    return out


GENERATORS = {
    1: _gen_g1,
    2: _gen_g2,
    3: _gen_g3,
    4: _gen_g4,
    5: _gen_g5,
    6: _gen_g6,
}


def generate_grade(grade: int, n: int = 500, seed: int = 42) -> List[RawItem]:
    rng = random.Random(seed + grade * 97)
    return GENERATORS[grade](n, rng)


# ---------- PDF extract (text-based grades) ----------

_EQ_RE = re.compile(
    r"^(\d+(?:\s*[+\-×÷]\s*\d+)+)\s*=\s*$"
)
_EQ_LOOSE = re.compile(
    r"(\d+(?:\s*[+\-×÷]\s*\d+)+)\s*="
)


def _pdf_dir() -> Path:
    # repo root / 1-6年级计算专项练习
    return Path(__file__).resolve().parents[4] / "1-6年级计算专项练习"


def extract_from_pdf_text(grade: int, topic: str, text: str) -> List[RawItem]:
    items: List[RawItem] = []
    seen = set()
    for line in text.splitlines():
        line = line.strip().replace("＋", "+").replace("－", "-")
        if not line or "练习" in line or "姓名" in line:
            continue
        for m in _EQ_LOOSE.finditer(line):
            expr = re.sub(r"\s+", " ", m.group(1)).strip()
            if expr in seen:
                continue
            try:
                val = eval_math_expr(expr)
                if val.denominator != 1:
                    ans = format_fraction(val)
                    kind = "fraction"
                else:
                    ans = str(val.numerator)
                    kind = "number"
                seen.add(expr)
                items.append(
                    RawItem(grade, topic, f"{expr} =", ans, kind, "pdf")
                )
            except Exception:
                continue
    return items


def load_pdf_items() -> List[RawItem]:
    root = _pdf_dir()
    if not root.is_dir():
        return []
    try:
        import fitz  # type: ignore
    except ImportError:
        return []

    collected: List[RawItem] = []
    for meta in GRADE_META:
        grade = meta["grade"]
        topic = meta["topic"]
        pdfs = sorted(root.glob(f"{grade}年级*.pdf"))
        if not pdfs:
            pdfs = [p for p in root.glob("*.pdf") if any(k in p.name for k in meta["pdf_keywords"])]
        for pdf in pdfs:
            try:
                doc = fitz.open(pdf)
                text = "".join(page.get_text() for page in doc)
                collected.extend(extract_from_pdf_text(grade, topic, text))
            except Exception:
                continue
    return collected


def build_bank(per_grade: int = 500) -> List[RawItem]:
    """合并 PDF 可解析题 + 按主题规则生成，保证每年级足量。"""
    by_grade: dict[int, List[RawItem]] = {g: [] for g in range(1, 7)}
    for item in load_pdf_items():
        by_grade[item.grade].append(item)

    out: List[RawItem] = []
    for grade in range(1, 7):
        existing = by_grade[grade]
        # 去重 stem
        stems = {x.stem for x in existing}
        need = max(0, per_grade - len(existing))
        generated = []
        for it in generate_grade(grade, n=need + 50):
            if it.stem not in stems:
                stems.add(it.stem)
                generated.append(it)
            if len(generated) >= need:
                break
        out.extend(existing)
        out.extend(generated[:need] if need else [])
        # 若 PDF 已超过 per_grade，仍全部保留（最多截断到 2*per_grade）
        if len(existing) > per_grade:
            # already added all existing; trim surplus generated only
            pass
    # 限制每年级上限，避免过大
    capped: List[RawItem] = []
    buckets: dict[int, List[RawItem]] = {g: [] for g in range(1, 7)}
    for it in out:
        buckets[it.grade].append(it)
    for g, lst in buckets.items():
        capped.extend(lst[: max(per_grade, min(len(lst), 1200))])
    return capped


def kp_label(grade: int, topic: str) -> str:
    return f"小学计算·{grade}年级·{topic}"


_MIXED_RE = re.compile(r"(-?)(\d+)又(\d+)/(\d+)")


def rewrite_mixed_to_slash(text: str) -> str:
    """把「1又2/3」改成「5/3」，便于用分数线显示；不改变题型本身。"""

    def _repl(m: re.Match) -> str:
        sign, whole, num, den = m.groups()
        f = Fraction(int(whole)) + Fraction(int(num), int(den))
        if sign == "-":
            f = -f
        return stem_fraction(f)

    return _MIXED_RE.sub(_repl, text or "")
