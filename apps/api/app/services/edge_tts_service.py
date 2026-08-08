"""Edge 神经 TTS（微软 Read Aloud）——无需 API Key，支持男女声与句间停顿。"""

from __future__ import annotations

import io
import re
from typing import Literal, Optional

Gender = Literal["female", "male"]
Lang = Literal["en", "zh"]

# 精选自然神经音色（美式英语 / 普通话）
_VOICES: dict[tuple[Lang, Gender], str] = {
    ("en", "female"): "en-US-JennyNeural",
    ("en", "male"): "en-US-GuyNeural",
    ("zh", "female"): "zh-CN-XiaoxiaoNeural",
    ("zh", "male"): "zh-CN-YunxiNeural",
}

_OPENAI_VOICE_GENDER: dict[str, Gender] = {
    "nova": "female",
    "shimmer": "female",
    "alloy": "female",
    "coral": "female",
    "verse": "female",
    "ballad": "female",
    "echo": "male",
    "onyx": "male",
    "fable": "male",
    "ash": "male",
}


def resolve_voice(
    *,
    gender: Optional[str] = None,
    voice: Optional[str] = None,
    lang: Optional[str] = None,
) -> tuple[str, Lang, Gender]:
    """解析最终 Edge 音色名。"""
    lang_key: Lang = "zh" if (lang or "").lower().startswith("zh") else "en"

    g: Gender = "female"
    if gender in ("male", "female"):
        g = gender  # type: ignore[assignment]
    elif voice:
        v = voice.strip().lower()
        if v in ("male", "female"):
            g = v  # type: ignore[assignment]
        elif v in _OPENAI_VOICE_GENDER:
            g = _OPENAI_VOICE_GENDER[v]
        elif "guy" in v or "davis" in v or "yunxi" in v or "yunjian" in v:
            g = "male"
        elif voice.endswith("Neural"):
            return voice, lang_key, g

    name = _VOICES[(lang_key, g)]
    return name, lang_key, g


_SENT_SPLIT = re.compile(
    r"(?<=[.!?…。！？；;])\s+|(?<=[.!?…。！？])(?=[A-Z\"“‘])"
)


def split_sentences(text: str) -> list[str]:
    raw = (text or "").strip()
    if not raw:
        return []
    if len(raw) <= 40 and not re.search(r"[.!?。！？]", raw):
        return [raw]
    parts = [p.strip() for p in _SENT_SPLIT.split(raw) if p and p.strip()]
    return parts or [raw]


def detect_lang(text: str, explicit: Optional[str] = None) -> Lang:
    if explicit and explicit.lower().startswith("zh"):
        return "zh"
    if explicit and explicit.lower().startswith("en"):
        return "en"
    if not text:
        return "en"
    hans = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    return "zh" if hans >= max(2, len(text) * 0.2) else "en"


def extract_headword(text: str) -> str:
    """只保留英文单词/短语本体，去掉音标、中文释义、词性等。"""
    s = (text or "").strip()
    if not s:
        return ""
    # 音标 /xxx/ [xxx]
    s = re.sub(r"/[^/\n]{1,40}/", " ", s)
    s = re.sub(r"\[[^\]]{1,40}\]", " ", s)
    # 中文
    s = re.sub(r"[\u4e00-\u9fff]+", " ", s)
    # 词性 (n.) (v.) (adj.) 等短括号
    s = re.sub(r"\([^)]{0,16}\)", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    # 取开头连续英文词（最多 6 个，覆盖短语）
    m = re.match(r"^([A-Za-z][A-Za-z'\-]*(?:\s+[A-Za-z][A-Za-z'\-]*){0,5})", s)
    if m:
        return m.group(1).strip()
    # 兜底：仅保留拉丁字母片段
    letters = re.findall(r"[A-Za-z][A-Za-z'\-]*", s)
    return " ".join(letters[:6]) if letters else ""


def normalize_rate(rate: Optional[str]) -> str:
    r = (rate or "-8%").strip()
    if re.fullmatch(r"[+-]?\d{1,3}%", r):
        return r if r[0] in "+-" else f"+{r}"
    return "-8%"


async def _stream_plain_mp3(text: str, voice: str, rate: str) -> bytes:
    """纯文本合成。切勿传入 SSML：edge-tts 会把标签当正文朗读。"""
    import edge_tts

    buf = io.BytesIO()
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    data = buf.getvalue()
    if not data:
        raise RuntimeError("Edge TTS 未返回音频")
    return data


async def synthesize_edge_mp3(
    text: str,
    *,
    gender: Optional[str] = None,
    voice: Optional[str] = None,
    lang: Optional[str] = None,
    rate: str = "-8%",
    mode: Optional[str] = None,
) -> tuple[bytes, dict]:
    """返回 (mp3_bytes, meta)。mode=word 时只读英文词头。"""
    try:
        import edge_tts  # noqa: F401
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("未安装 edge-tts，请执行: pip install edge-tts") from e

    clean = (text or "").strip()
    if not clean:
        raise ValueError("文本为空")

    if (mode or "").lower() in ("word", "headword", "vocab"):
        clean = extract_headword(clean)
        if not clean:
            raise ValueError("未识别到可朗读的英文单词")

    lang_key = detect_lang(clean, lang)
    # 单词模式强制英语音色，避免误判中文
    if (mode or "").lower() in ("word", "headword", "vocab"):
        lang_key = "en"

    voice_name, lang_key, g = resolve_voice(gender=gender, voice=voice, lang=lang_key)
    rate_n = normalize_rate(rate)
    parts = split_sentences(clean)

    # 分句分别合成再拼接，形成自然停顿（不用 SSML，避免标签被读出）
    audio_parts: list[bytes] = []
    for part in parts:
        audio_parts.append(await _stream_plain_mp3(part, voice_name, rate_n))
    data = b"".join(audio_parts)

    return data, {
        "engine": "edge",
        "voice": voice_name,
        "gender": g,
        "lang": lang_key,
        "mode": (mode or "sentence"),
        "text": clean,
        "sentences": len(parts),
    }


def list_preset_voices() -> list[dict]:
    return [
        {"id": "female", "label": "女声", "edge": _VOICES[("en", "female")], "lang": "en"},
        {"id": "male", "label": "男声", "edge": _VOICES[("en", "male")], "lang": "en"},
        {
            "id": "female_zh",
            "label": "女声（中文）",
            "edge": _VOICES[("zh", "female")],
            "lang": "zh",
            "gender": "female",
        },
        {
            "id": "male_zh",
            "label": "男声（中文）",
            "edge": _VOICES[("zh", "male")],
            "lang": "zh",
            "gender": "male",
        },
    ]
