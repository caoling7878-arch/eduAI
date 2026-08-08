from __future__ import annotations

"""动词变形：进行时 -ing / 过去式 / 过去分词。"""

import re
from typing import Dict, Optional, Tuple

# 常见不规则动词：base -> (past, past_participle, optional ing override)
_IRREGULAR: Dict[str, Tuple[str, str, Optional[str]]] = {
    "be": ("was/were", "been", "being"),
    "become": ("became", "become", None),
    "begin": ("began", "begun", None),
    "break": ("broke", "broken", None),
    "bring": ("brought", "brought", None),
    "build": ("built", "built", None),
    "buy": ("bought", "bought", None),
    "catch": ("caught", "caught", None),
    "choose": ("chose", "chosen", None),
    "come": ("came", "come", None),
    "cost": ("cost", "cost", None),
    "cut": ("cut", "cut", "cutting"),
    "do": ("did", "done", None),
    "draw": ("drew", "drawn", None),
    "drink": ("drank", "drunk", None),
    "drive": ("drove", "driven", None),
    "eat": ("ate", "eaten", None),
    "fall": ("fell", "fallen", None),
    "feel": ("felt", "felt", None),
    "find": ("found", "found", None),
    "fly": ("flew", "flown", None),
    "forget": ("forgot", "forgotten", None),
    "get": ("got", "got/gotten", "getting"),
    "give": ("gave", "given", None),
    "go": ("went", "gone", None),
    "grow": ("grew", "grown", None),
    "have": ("had", "had", "having"),
    "hear": ("heard", "heard", None),
    "hide": ("hid", "hidden", None),
    "hit": ("hit", "hit", "hitting"),
    "hold": ("held", "held", None),
    "hurt": ("hurt", "hurt", None),
    "keep": ("kept", "kept", None),
    "know": ("knew", "known", None),
    "leave": ("left", "left", None),
    "lend": ("lent", "lent", None),
    "let": ("let", "let", "letting"),
    "lie": ("lay", "lain", "lying"),  # 躺；撒谎规则见下
    "lose": ("lost", "lost", None),
    "make": ("made", "made", None),
    "mean": ("meant", "meant", None),
    "meet": ("met", "met", None),
    "pay": ("paid", "paid", None),
    "put": ("put", "put", "putting"),
    "read": ("read", "read", None),
    "ride": ("rode", "ridden", None),
    "ring": ("rang", "rung", None),
    "rise": ("rose", "risen", None),
    "run": ("ran", "run", "running"),
    "say": ("said", "said", None),
    "see": ("saw", "seen", None),
    "sell": ("sold", "sold", None),
    "send": ("sent", "sent", None),
    "set": ("set", "set", "setting"),
    "shine": ("shone", "shone", None),
    "show": ("showed", "shown/showed", None),
    "shut": ("shut", "shut", "shutting"),
    "sing": ("sang", "sung", None),
    "sit": ("sat", "sat", "sitting"),
    "sleep": ("slept", "slept", None),
    "speak": ("spoke", "spoken", None),
    "spend": ("spent", "spent", None),
    "stand": ("stood", "stood", None),
    "steal": ("stole", "stolen", None),
    "swim": ("swam", "swum", "swimming"),
    "take": ("took", "taken", None),
    "teach": ("taught", "taught", None),
    "tell": ("told", "told", None),
    "think": ("thought", "thought", None),
    "throw": ("threw", "thrown", None),
    "understand": ("understood", "understood", None),
    "wake": ("woke", "woken", None),
    "wear": ("wore", "worn", None),
    "win": ("won", "won", "winning"),
    "write": ("wrote", "written", None),
    "bear": ("bore", "born/borne", None),
    "beat": ("beat", "beaten", None),
    "blow": ("blew", "blown", None),
    "burn": ("burnt/burned", "burnt/burned", None),
    "dig": ("dug", "dug", "digging"),
    "dream": ("dreamt/dreamed", "dreamt/dreamed", None),
    "fight": ("fought", "fought", None),
    "forbid": ("forbade", "forbidden", None),
    "freeze": ("froze", "frozen", None),
    "hang": ("hung", "hung", None),
    "lay": ("laid", "laid", None),
    "lead": ("led", "led", None),
    "learn": ("learnt/learned", "learnt/learned", None),
    "light": ("lit/lighted", "lit/lighted", None),
    "prefer": ("preferred", "preferred", "preferring"),
    "quit": ("quit/quitted", "quit/quitted", "quitting"),
    "shake": ("shook", "shaken", None),
    "shoot": ("shot", "shot", None),
    "sink": ("sank", "sunk", None),
    "smell": ("smelt/smelled", "smelt/smelled", None),
    "spell": ("spelt/spelled", "spelt/spelled", None),
    "spill": ("spilt/spilled", "spilt/spilled", None),
    "spoil": ("spoilt/spoiled", "spoilt/spoiled", None),
    "spread": ("spread", "spread", None),
    "stick": ("stuck", "stuck", None),
    "strike": ("struck", "struck/stricken", None),
    "sweep": ("swept", "swept", None),
    "swing": ("swung", "swung", None),
    "tear": ("tore", "torn", None),
    "weep": ("wept", "wept", None),
}


def is_verb_pos(pos: str) -> bool:
    """判断词性是否含动词（排除 adv. 等误伤）。"""
    for part in re.split(r"[/·,，]", (pos or "").lower()):
        p = part.strip()
        if not p:
            continue
        if p in ("v", "v.", "vt", "vt.", "vi", "vi.", "verb"):
            return True
        if p.startswith(("vt.", "vi.", "v.")):
            return True
    return False


_DOUBLING = {
    "stop",
    "plan",
    "drop",
    "shop",
    "hop",
    "rob",
    "nod",
    "pad",
    "wrap",
    "trip",
    "clap",
    "grab",
    "stir",
    "prefer",
    "refer",
    "occur",
    "commit",
    "control",
    "travel",  # BrE travelling；此处用美式 traveling 规则另行处理
}


def _ends_cvc(word: str) -> bool:
    """单音节或重读末尾辅+元+辅，且末辅非 w/x/y。"""
    if len(word) < 3:
        return False
    a, b, c = word[-3], word[-2], word[-1]
    vowels = set("aeiou")
    return c not in vowels and c not in "wxy" and b in vowels and a not in vowels


def _ing(base: str) -> str:
    w = base.lower()
    if w.endswith("ie"):
        return w[:-2] + "ying"
    if w.endswith("e") and not w.endswith(("ee", "oe", "ye")):
        return w[:-1] + "ing"
    if w.endswith("c"):
        return w + "king"
    if w in _DOUBLING or (_ends_cvc(w) and len(w) <= 5):
        return w + w[-1] + "ing"
    return w + "ing"


def _ed(base: str) -> str:
    w = base.lower()
    if w.endswith("e"):
        return w + "d"
    if w.endswith("y") and len(w) > 1 and w[-2] not in "aeiou":
        return w[:-1] + "ied"
    if w.endswith("c"):
        return w + "ked"
    if w in _DOUBLING or (_ends_cvc(w) and len(w) <= 5):
        return w + w[-1] + "ed"
    return w + "ed"


def conjugate(word: str) -> Optional[Dict[str, str]]:
    """返回 {ing, past, past_participle}；非词干时仍按规则生成。"""
    base = (word or "").strip().lower()
    if not base or " " in base:
        return None
    if base in _IRREGULAR:
        past, pp, ing_override = _IRREGULAR[base]
        return {
            "ing": ing_override or _ing(base),
            "past": past,
            "past_participle": pp,
        }
    past = _ed(base)
    return {
        "ing": _ing(base),
        "past": past,
        "past_participle": past,
    }


def conjugations_for(word: str, pos: str) -> Optional[Dict[str, str]]:
    if not is_verb_pos(pos):
        return None
    return conjugate(word)
