from __future__ import annotations

"""词根词缀拆解：长单词分段 + 图画联想标注。"""

import json
from typing import Any, Dict, List, Optional

from .word_image import resolve_theme, theme_icon, theme_label

# 前缀：越长越优先匹配
PREFIXES: List[tuple[str, str, str]] = [
    ("inter", "互相；之间", "cross"),
    ("trans", "跨越；转移", "arrow"),
    ("under", "在…之下", "down"),
    ("super", "超；在上", "up"),
    ("tele", "远距离", "line"),
    ("after", "在…之后", "after"),
    ("over", "过度；在上", "over"),
    ("anti", "反对；抗", "shield"),
    ("auto", "自己；自动", "gear"),
    ("micro", "微小", "dot"),
    ("multi", "多", "dots"),
    ("semi", "半", "half"),
    ("post", "后", "after"),
    ("pre", "预先", "before"),
    ("pro", "向前；赞成", "forward"),
    ("dis", "否定；分开", "cross"),
    ("mis", "错误", "warn"),
    ("non", "非；不", "cross"),
    ("sub", "下；次", "down"),
    ("out", "向外；超过", "out"),
    ("geo", "大地；地理", "globe"),
    ("bio", "生命；生物", "animal"),
    ("bi", "双；二", "two"),
    ("co", "共同", "link"),
    ("de", "去掉；向下", "down"),
    ("en", "使…", "spark"),
    ("ex", "向外；前任", "out"),
    ("re", "再；回", "loop"),
    ("un", "否定；相反", "cross"),
    ("in", "不；进入", "in"),
    ("im", "不；进入", "cross"),
    ("il", "不", "cross"),
    ("ir", "不", "cross"),
]

# 后缀
SUFFIXES: List[tuple[str, str, str]] = [
    ("tion", "名词：行为/状态", "box"),
    ("sion", "名词：行为/状态", "box"),
    ("ment", "名词：结果/手段", "box"),
    ("ness", "名词：性质", "box"),
    ("able", "可…的", "ok"),
    ("ible", "可…的", "ok"),
    ("ance", "名词：状态", "box"),
    ("ence", "名词：状态", "box"),
    ("hood", "名词：身份/状态", "box"),
    ("ship", "名词：关系/状态", "link"),
    ("ful", "充满…的", "full"),
    ("less", "没有…的", "empty"),
    ("ous", "具有…的", "star"),
    ("ive", "有…倾向的", "star"),
    ("ize", "使…化", "spark"),
    ("ise", "使…化", "spark"),
    ("ity", "名词：性质", "box"),
    ("ety", "名词：性质", "box"),
    ("ial", "…的", "star"),
    ("ical", "…的", "star"),
    ("ally", "…地", "dot"),
    ("ing", "进行/动名词", "wave"),
    ("ed", "过去/被动", "dot"),
    ("ly", "…地", "dot"),
    ("er", "人/比较级", "person"),
    ("or", "人/物", "person"),
    ("ist", "从事…的人", "person"),
    ("ian", "相关的人/…的", "person"),
    ("ese", "…的人/语言", "globe"),
    ("ish", "稍带…的/…的", "star"),
    ("al", "…的", "star"),
    ("ic", "…的", "star"),
    ("y", "名词/形容词化", "dot"),
]

# 词根提示（常见词根）
ROOTS: Dict[str, tuple[str, str]] = {
    "happy": ("开心", "smile"),
    "phone": ("听筒；声音", "phone"),
    "ject": ("投；抛", "throw"),
    "sect": ("切；割", "cut"),
    "graph": ("写；画", "pen"),
    "meter": ("测量", "ruler"),
    "port": ("携带", "bag"),
    "spect": ("看", "eye"),
    "vis": ("看", "eye"),
    "vid": ("看", "eye"),
    "dict": ("说", "speak"),
    "scrib": ("写", "pen"),
    "script": ("写", "pen"),
    "form": ("形状", "shape"),
    "struct": ("建造", "build"),
    "tract": ("拉；抽", "pull"),
    "duc": ("引导", "lead"),
    "duct": ("引导", "lead"),
    "pos": ("放", "place"),
    "pose": ("放", "place"),
    "press": ("压", "press"),
    "cur": ("跑；发生", "run"),
    "vert": ("竖直；转", "vertical"),
    "vers": ("转", "turn"),
    "angle": ("角", "angle"),
    "plane": ("平面", "plane"),
    "metr": ("测量", "ruler"),
    "accur": ("精确", "target"),
    "demonstr": ("展示；证明", "board"),
    "class": ("班级", "school"),
    "school": ("学校", "school"),
    "home": ("家", "house"),
    "work": ("工作", "build"),
    "room": ("房间", "house"),
    "book": ("书", "book"),
    "play": ("玩", "sport"),
    "ground": ("地面", "nature"),
    "friend": ("朋友", "person"),
    "teach": ("教", "school"),
    "learn": ("学", "school"),
    "study": ("学习", "book"),
    "read": ("读", "book"),
    "write": ("写", "pen"),
    "know": ("知道", "eye"),
    "think": ("思考", "spark"),
    "feel": ("感觉", "smile"),
    "help": ("帮助", "link"),
    "move": ("移动", "run"),
    "build": ("建造", "build"),
    "light": ("光", "spark"),
    "dark": ("暗", "empty"),
    "water": ("水", "nature"),
    "land": ("陆地", "globe"),
    "hand": ("手", "body"),
    "foot": ("脚", "body"),
    "head": ("头", "body"),
    "eye": ("眼睛", "eye"),
    "day": ("日", "time"),
    "night": ("夜", "time"),
    "year": ("年", "time"),
    "week": ("周", "time"),
    "time": ("时间", "time"),
    "nation": ("国家", "globe"),
    "person": ("人", "person"),
    "act": ("行动", "run"),
    "use": ("使用", "gear"),
    "view": ("看", "eye"),
    "sign": ("标记", "pen"),
    "part": ("部分", "half"),
    "point": ("点", "dot"),
    "place": ("地方", "place"),
    "side": ("边", "shape"),
    "line": ("线", "line"),
    "number": ("数字", "ruler"),
    "color": ("颜色", "color"),
    "sound": ("声音", "speak"),
}


# 常见合成词（中学词表高频）
COMPOUNDS: Dict[str, List[tuple[str, str, str]]] = {
    "classmate": [("class", "班级", "school"), ("mate", "伙伴", "person")],
    "classroom": [("class", "班级", "school"), ("room", "房间", "house")],
    "homework": [("home", "家", "house"), ("work", "作业/工作", "book")],
    "textbook": [("text", "课文", "book"), ("book", "书", "book")],
    "notebook": [("note", "笔记", "pen"), ("book", "本", "book")],
    "blackboard": [("black", "黑", "color"), ("board", "板", "board")],
    "playground": [("play", "玩耍", "sport"), ("ground", "场地", "nature")],
    "breakfast": [("break", "打断", "cut"), ("fast", "禁食", "food")],
    "football": [("foot", "脚", "body"), ("ball", "球", "sport")],
    "basketball": [("basket", "篮", "box"), ("ball", "球", "sport")],
    "headache": [("head", "头", "body"), ("ache", "痛", "health")],
    "toothbrush": [("tooth", "牙", "body"), ("brush", "刷", "item")],
    "keyboard": [("key", "键", "item"), ("board", "板", "board")],
    "afternoon": [("after", "在…后", "after"), ("noon", "正午", "time")],
    "weekend": [("week", "周", "time"), ("end", "结束", "dot")],
    "sometimes": [("some", "一些", "dots"), ("times", "次数/时候", "time")],
    "grandfather": [("grand", "祖辈", "up"), ("father", "父亲", "family")],
    "grandmother": [("grand", "祖辈", "up"), ("mother", "母亲", "family")],
    "grandparent": [("grand", "祖辈", "up"), ("parent", "父母", "family")],
    "bedroom": [("bed", "床", "item"), ("room", "房间", "house")],
    "bathroom": [("bath", "洗浴", "water"), ("room", "房间", "house")],
    "housework": [("house", "家", "house"), ("work", "事务", "build")],
    "sunshine": [("sun", "太阳", "nature"), ("shine", "照耀", "spark")],
    "rainbow": [("rain", "雨", "nature"), ("bow", "弧", "color")],
    "newspaper": [("news", "新闻", "speak"), ("paper", "纸", "book")],
    "policeman": [("police", "警察", "shield"), ("man", "人", "person")],
    "fireman": [("fire", "火", "spark"), ("man", "人", "person")],
    "bookstore": [("book", "书", "book"), ("store", "商店", "shop")],
    "supermarket": [("super", "超级", "up"), ("market", "市场", "shop")],
    "understand": [("under", "在…下", "down"), ("stand", "站立/承受", "person")],
    "forget": [("for", "离去", "out"), ("get", "得到", "bag")],
    "forgive": [("for", "向前/放弃", "forward"), ("give", "给", "link")],
    "outside": [("out", "外", "out"), ("side", "边", "shape")],
    "inside": [("in", "内", "in"), ("side", "边", "shape")],
    "everyone": [("every", "每", "dots"), ("one", "一人", "person")],
    "someone": [("some", "某", "dots"), ("one", "一人", "person")],
    "nothing": [("no", "无", "cross"), ("thing", "事物", "box")],
    "something": [("some", "某", "dots"), ("thing", "事物", "box")],
    "everything": [("every", "每", "dots"), ("thing", "事物", "box")],
    "birthday": [("birth", "出生", "spark"), ("day", "日子", "time")],
    "yesterday": [("yester", "先前的", "before"), ("day", "日子", "time")],
    "today": [("to", "这/到", "forward"), ("day", "日子", "time")],
    "tonight": [("to", "这/到", "forward"), ("night", "夜晚", "time")],
    "airport": [("air", "空中", "out"), ("port", "港口", "bag")],
    "railway": [("rail", "铁轨", "line"), ("way", "路", "forward")],
    "highway": [("high", "高", "up"), ("way", "路", "forward")],
    "bedroom": [("bed", "床", "item"), ("room", "房间", "house")],
}


CURATED: Dict[str, Dict[str, Any]] = {
    "unhappy": {
        "segments": [
            {"text": "un", "type": "prefix", "gloss": "否定", "icon": "cross", "color": "#C45C26"},
            {"text": "happy", "type": "root", "gloss": "开心", "icon": "smile", "color": "#0F6B5C"},
        ],
        "story": "un（否定，画 ×）+ happy（笑脸）→ 不开心",
        "image_key": "unhappy",
    },
    "telephone": {
        "segments": [
            {"text": "tele", "type": "prefix", "gloss": "远距离", "icon": "line", "color": "#2A8FBD"},
            {"text": "phone", "type": "root", "gloss": "听筒", "icon": "phone", "color": "#0F6B5C"},
        ],
        "story": "tele（远距离，画长线）+ phone（听筒）→ 远距离通话 = 电话",
        "image_key": "telephone",
    },
    "projection": {
        "segments": [
            {"text": "pro", "type": "prefix", "gloss": "向前", "icon": "forward", "color": "#2A8FBD"},
            {"text": "ject", "type": "root", "gloss": "投掷", "icon": "throw", "color": "#0F6B5C"},
            {"text": "ion", "type": "suffix", "gloss": "名词化", "icon": "box", "color": "#E8A317"},
        ],
        "story": "向前投出的影子 → 投影 / 射影",
        "image_key": "projection",
    },
    "geometry": {
        "segments": [
            {"text": "geo", "type": "prefix", "gloss": "大地", "icon": "globe", "color": "#0F6B5C"},
            {"text": "metr", "type": "root", "gloss": "测量", "icon": "ruler", "color": "#2A8FBD"},
            {"text": "y", "type": "suffix", "gloss": "学科", "icon": "box", "color": "#E8A317"},
        ],
        "story": "测量大地的学问 → 几何",
        "image_key": "geometry",
    },
    "intersect": {
        "segments": [
            {"text": "inter", "type": "prefix", "gloss": "互相", "icon": "cross", "color": "#2A8FBD"},
            {"text": "sect", "type": "root", "gloss": "切开", "icon": "cut", "color": "#0F6B5C"},
        ],
        "story": "彼此切入 → 相交",
        "image_key": "intersect",
    },
    "demonstrate": {
        "segments": [
            {"text": "de", "type": "prefix", "gloss": "完全地", "icon": "spark", "color": "#2A8FBD"},
            {"text": "monstr", "type": "root", "gloss": "展示", "icon": "board", "color": "#0F6B5C"},
            {"text": "ate", "type": "suffix", "gloss": "使成为", "icon": "spark", "color": "#E8A317"},
        ],
        "story": "完全展示出来 → 证明 / 演示",
        "image_key": "demonstrate",
    },
    "accurate": {
        "segments": [
            {"text": "ac", "type": "prefix", "gloss": "朝向", "icon": "forward", "color": "#2A8FBD"},
            {"text": "cur", "type": "root", "gloss": "关心；照料", "icon": "target", "color": "#0F6B5C"},
            {"text": "ate", "type": "suffix", "gloss": "具有…性质", "icon": "ok", "color": "#E8A317"},
        ],
        "story": "照料到位 → 准确的",
        "image_key": "accurate",
    },
    "vertical": {
        "segments": [
            {"text": "vert", "type": "root", "gloss": "竖直 / 顶点", "icon": "vertical", "color": "#0F6B5C"},
            {"text": "ical", "type": "suffix", "gloss": "…的", "icon": "star", "color": "#E8A317"},
        ],
        "story": "朝顶点方向 → 垂直的",
        "image_key": "vertical",
    },
    "angle": {
        "segments": [
            {"text": "angle", "type": "root", "gloss": "角", "icon": "angle", "color": "#0F6B5C"},
        ],
        "story": "两条线相交形成的开口 → 角",
        "image_key": "angle",
    },
    "plane": {
        "segments": [
            {"text": "plane", "type": "root", "gloss": "平坦面", "icon": "plane", "color": "#0F6B5C"},
        ],
        "story": "平展的面 → 平面",
        "image_key": "plane",
    },
}


def _seg(text: str, typ: str, gloss: str, icon: str, color: str) -> Dict[str, str]:
    return {"text": text, "type": typ, "gloss": gloss, "icon": icon, "color": color}


def _is_strong(data: Dict[str, Any]) -> bool:
    segs = data.get("segments") or []
    story = (data.get("story") or "").strip()
    if len(segs) >= 2:
        return True
    if story and not data.get("auto") and len(segs) == 1:
        return True
    return False


def _from_compound(word: str) -> Optional[Dict[str, Any]]:
    w = word.lower().strip()
    if w not in COMPOUNDS:
        return None
    colors = {"prefix": "#2A8FBD", "root": "#0F6B5C", "suffix": "#E8A317"}
    segments = []
    for i, (text, gloss, icon) in enumerate(COMPOUNDS[w]):
        typ = "root" if i == 0 else ("root" if i == len(COMPOUNDS[w]) - 1 and i > 0 else "root")
        color = colors["prefix"] if i == 0 else (colors["suffix"] if i == len(COMPOUNDS[w]) - 1 else colors["root"])
        if i == 0:
            typ, color = "prefix" if len(COMPOUNDS[w]) > 1 else "root", colors["prefix"] if len(COMPOUNDS[w]) > 1 else colors["root"]
        elif i == len(COMPOUNDS[w]) - 1:
            typ, color = "root", colors["root"]
        segments.append(_seg(text, typ if i else ("prefix" if len(COMPOUNDS[w]) > 1 else "root"), gloss, icon, color if i else colors["prefix"]))
    # simplify typing: first piece prefix-like, rest root
    fixed = []
    for i, (text, gloss, icon) in enumerate(COMPOUNDS[w]):
        typ = "prefix" if i == 0 and len(COMPOUNDS[w]) > 1 else "root"
        color = colors["prefix"] if typ == "prefix" else colors["root"]
        if i == len(COMPOUNDS[w]) - 1 and i > 0:
            color = colors["suffix"] if typ != "prefix" else colors["root"]
        fixed.append(_seg(text, typ, gloss, icon, color))
    story_bits = " + ".join(f"{t}（{g}）" for t, g, _ in COMPOUNDS[w])
    return {
        "segments": fixed,
        "story": f"{story_bits} → 合成词记忆",
        "image_key": w,
        "auto": True,
    }


def _heuristic(word: str, meaning: str = "") -> Optional[Dict[str, Any]]:
    w = word.lower().strip().replace(" ", "")
    if len(w) < 4:
        return None
    rest = w
    segments: List[Dict[str, str]] = []
    colors = {"prefix": "#2A8FBD", "root": "#0F6B5C", "suffix": "#E8A317"}

    for pref, gloss, icon in PREFIXES:
        min_rest = 2 if len(w) <= 6 else 3
        if rest.startswith(pref) and len(rest) - len(pref) >= min_rest:
            # 避免把 in/to 等过短词根切坏：短词更谨慎
            if len(pref) <= 2 and len(w) < 6:
                continue
            segments.append(_seg(pref, "prefix", gloss, icon, colors["prefix"]))
            rest = rest[len(pref) :]
            break

    suffix_parts: List[Dict[str, str]] = []
    for suf, gloss, icon in SUFFIXES:
        min_rest = 2 if len(w) <= 6 else 3
        if rest.endswith(suf) and len(rest) - len(suf) >= min_rest:
            if len(suf) <= 2 and len(w) < 6 and suf not in ("er", "or", "ly", "y"):
                continue
            suffix_parts.insert(0, _seg(suf, "suffix", gloss, icon, colors["suffix"]))
            rest = rest[: -len(suf)]
            break

    if not rest:
        return None

    root_gloss, root_icon = ROOTS.get(rest, ("", ""))
    if not root_gloss:
        for key, (g, ic) in sorted(ROOTS.items(), key=lambda x: -len(x[0])):
            if rest == key or rest.startswith(key) or (len(key) >= 4 and key in rest):
                root_gloss, root_icon = g, ic
                break
    if not root_gloss:
        # 用中文释义当词根提示
        gloss = (meaning or "").split("；")[0].split("，")[0][:10] or f"词根「{rest}」"
        theme = resolve_theme(word, meaning)
        root_gloss, root_icon = gloss, theme_icon(theme)

    segments.append(_seg(rest, "root", root_gloss, root_icon, colors["root"]))
    segments.extend(suffix_parts)

    if len(segments) < 2:
        return None

    story_bits = " + ".join(f"{s['text']}（{s['gloss']}）" for s in segments)
    meaning_hint = (meaning or "").split("；")[0].split("，")[0]
    story = f"{story_bits} → {meaning_hint or '拆解记忆'}"
    return {
        "segments": segments,
        "story": story,
        "image_key": resolve_theme(word, meaning),
        "auto": True,
    }


def _meaning_mnemonic(word: str, meaning: str = "") -> Dict[str, Any]:
    theme = resolve_theme(word, meaning)
    gloss = (meaning or "").split("；")[0].split("，")[0][:14] or "整词记忆"
    label = theme_label(theme)
    return {
        "segments": [
            _seg(word.lower(), "root", gloss, theme_icon(theme), "#0F6B5C"),
        ],
        "story": f"图画记忆（{label}）：{gloss} → {word}",
        "image_key": theme,
        "auto": True,
        "mnemonic": True,
    }


def morph_for(word: str, stored_json: str = "", meaning: str = "") -> Dict[str, Any]:
    """优先精选词表 / 合成词 / 启发式拆解；弱存储则回退；短词用词义图画记忆。"""
    key = word.lower().strip()

    if key in CURATED:
        data = dict(CURATED[key])
        data["image_key"] = resolve_theme(word, meaning, data.get("image_key", key))
        return data

    compound = _from_compound(key)
    if compound:
        compound["image_key"] = resolve_theme(word, meaning, compound.get("image_key", key))
        return compound

    heur = _heuristic(key, meaning)
    if heur:
        return heur

    # 强存储（手工多段）才采用
    if stored_json and stored_json.strip() not in ("", "{}", "null"):
        try:
            data = json.loads(stored_json)
            if isinstance(data, dict) and _is_strong(data):
                data.setdefault("image_key", resolve_theme(word, meaning, data.get("image_key", key)))
                data.setdefault("story", "")
                return data
        except json.JSONDecodeError:
            pass

    return _meaning_mnemonic(word, meaning)


def morph_json_dumps(data: Dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False)
