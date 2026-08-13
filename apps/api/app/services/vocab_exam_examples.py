from __future__ import annotations

"""从北京中考英语真题语料中为单词匹配真实例句（单项 / 完形 / 阅读原句）。"""

import re
from functools import lru_cache
from typing import Dict, List, Optional, Sequence, Tuple

from .beijing_zhongkao_corpus import CORPUS, _zh_map
from .verb_forms import conjugate

_TOKEN = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")

IRREGULAR_NOUNS = {
    "child": ["children"],
    "man": ["men"],
    "woman": ["women"],
    "person": ["people", "persons"],
    "foot": ["feet"],
    "tooth": ["teeth"],
    "mouse": ["mice"],
    "goose": ["geese"],
    "leaf": ["leaves"],
    "life": ["lives"],
    "knife": ["knives"],
    "wife": ["wives"],
    "half": ["halves"],
    "shelf": ["shelves"],
    "wolf": ["wolves"],
    "thief": ["thieves"],
    "self": ["selves"],
    "fish": ["fish", "fishes"],
    "sheep": ["sheep"],
    "Chinese": ["Chinese"],
    "Japanese": ["Japanese"],
}

# 太短或功能词不单独用真题句去「硬配」，避免 a/the 命中整卷
SKIP_WORDS = {
    "a", "an", "the", "of", "to", "in", "on", "at", "for", "and", "or", "but",
    "is", "are", "was", "were", "be", "been", "being", "am", "do", "does", "did",
    "have", "has", "had", "will", "would", "can", "could", "should", "may",
    "might", "must", "i", "you", "he", "she", "it", "we", "they", "me", "him",
    "her", "us", "them", "my", "your", "his", "its", "our", "their", "this",
    "that", "these", "those", "not", "no", "yes", "as", "if", "so", "than",
}


def _noun_forms(word: str) -> List[str]:
    w = (word or "").lower().strip()
    out = [w]
    out.extend(IRREGULAR_NOUNS.get(w, []))
    if w.endswith("y") and len(w) > 1 and w[-2] not in "aeiou":
        out.append(w[:-1] + "ies")
    elif w.endswith(("s", "x", "z", "ch", "sh")):
        out.append(w + "es")
    elif w.endswith("fe"):
        out.append(w[:-2] + "ves")
    elif w.endswith("f"):
        out.append(w[:-1] + "ves")
    else:
        out.append(w + "s")
    return list(dict.fromkeys(out))


def word_forms(word: str) -> List[str]:
    w = (word or "").lower().strip()
    if not w:
        return []
    forms = set(_noun_forms(w))
    conj = conjugate(w) or {}
    for key in ("ing", "past", "past_participle"):
        val = str(conj.get(key) or "")
        for piece in re.split(r"[/，,]", val):
            p = piece.strip().lower()
            if p:
                forms.add(p)
    if not w.endswith("s"):
        forms.add(w + "es")
        forms.add(w + "ed")
        forms.add(w + "ing")
    return [f for f in forms if f and f.isalpha() or "'" in f]


def _pos_score(sentence: str, form: str, pos: str) -> int:
    """粗略按词性给真题句打分，便于一词多义时选不同原句。"""
    s = f" {sentence} "
    fl = re.escape(form)
    p = (pos or "").lower()
    score = 0
    if p.startswith("v"):
        if re.search(rf"\b(to|will|can|could|should|must|may|might)\s+{fl}\b", s, re.I):
            score += 6
        if re.search(rf"\b(i|you|we|they|he|she|it)\s+{fl}\b", s, re.I):
            score += 4
        if form.endswith(("ed", "ing")):
            score += 3
    elif p.startswith("n"):
        if re.search(rf"\b(a|an|the|my|your|his|her|our|their|this|that)\s+{fl}\b", s, re.I):
            score += 5
        if form.endswith("s") and not form.endswith("ss"):
            score += 2
    elif p.startswith("adj"):
        if re.search(rf"\b(is|are|was|were|be|been|feel|looks?|seems?)\s+{fl}\b", s, re.I):
            score += 5
        if re.search(rf"\b{fl}\s+[a-z]+", s, re.I):
            score += 2
    elif p.startswith("adv"):
        if form.endswith("ly"):
            score += 5
    return score


@lru_cache(maxsize=1)
def _index() -> Dict[str, List[int]]:
    idx: Dict[str, List[int]] = {}
    for i, item in enumerate(CORPUS):
        seen = set()
        for tok in _TOKEN.findall(item["en"] or ""):
            key = tok.lower()
            if key in seen:
                continue
            seen.add(key)
            idx.setdefault(key, []).append(i)
    return idx


def lookup_exam_examples(
    word: str,
    pos: str = "",
    limit: int = 4,
    used_ids: Optional[Sequence[int]] = None,
) -> List[dict]:
    key = (word or "").lower().strip()
    if not key or key in SKIP_WORDS:
        return []
    idx = _index()
    used = set(used_ids or [])
    parts = [p for p in key.split() if p and p not in SKIP_WORDS]
    candidates: List[Tuple[int, int, int]] = []  # score, -len, corpus_id
    if parts and len(parts) >= 2:
        scan_ids = range(len(CORPUS))
        form_for_score = parts[0]
    else:
        scan_ids = []
        seen_c = set()
        for form in word_forms(key):
            for cid in idx.get(form, []):
                if cid not in seen_c:
                    seen_c.add(cid)
                    scan_ids.append(cid)
        form_for_score = key
    for cid in scan_ids:
        if cid in used:
            continue
        item = CORPUS[cid]
        en = item["en"]
        if len(en) < 22 or len(en) > 220:
            continue
        if parts and len(parts) >= 2:
            low = en.lower()
            if not all(re.search(rf"\b{re.escape(p)}\b", low) for p in parts):
                continue
            form_for_score = parts[0]
        score = 8 + _pos_score(en, form_for_score, pos)
        # 完形/阅读比单项更能体现词义
        if item.get("section") in ("cloze", "reading"):
            score += 3
        # 更短、更适合词卡
        if 30 <= len(en) <= 140:
            score += 2
        candidates.append((score, -len(en), cid))
    candidates.sort(reverse=True)
    out = []
    seen_en = set()
    for _, __, cid in candidates:
        item = CORPUS[cid]
        en = item["en"].strip()
        if en.lower() in seen_en:
            continue
        seen_en.add(en.lower())
        cn = (item.get("cn") or "").strip()
        if not cn:
            zh = _zh_map()
            cn = zh.get(en) or zh.get(en.lower()) or ""
        out.append(
            {
                "id": cid,
                "en": en,
                "cn": cn,
                "year": item.get("year") or "",
                "section": item.get("section") or "",
                "source": f"北京中考{item.get('year')}",
            }
        )
        if len(out) >= limit:
            break
    return out
