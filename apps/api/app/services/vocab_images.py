from __future__ import annotations

"""单词真实配图：来自「带配图」docx 的 JPG 映射。"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

_STATIC_DIR = Path(__file__).resolve().parents[1] / "static" / "vocab"
_MAP_PATH = Path(__file__).resolve().parents[1] / "data" / "vocab_image_map.json"


@lru_cache(maxsize=1)
def _load_map() -> dict[str, str]:
    if not _MAP_PATH.exists():
        return {}
    try:
        data = json.loads(_MAP_PATH.read_text(encoding="utf-8"))
        return {str(k).lower(): str(v) for k, v in data.items()} if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def photo_filename(word: str) -> Optional[str]:
    key = (word or "").strip().lower()
    if not key:
        return None
    mapping = _load_map()
    if key in mapping:
        return mapping[key]
    # 空格/连字符变体
    alt = key.replace("-", " ")
    if alt in mapping:
        return mapping[alt]
    alt2 = key.replace(" ", "_")
    for k, v in mapping.items():
        if k.replace(" ", "_") == alt2:
            return v
    return None


def photo_url(word: str) -> Optional[str]:
    """返回前端可访问的静态 URL（经 /api/v1 代理）。"""
    fname = photo_filename(word)
    if not fname:
        return None
    path = _STATIC_DIR / fname
    if not path.is_file():
        return None
    return f"/api/v1/static/vocab/{fname}"


def clear_photo_cache() -> None:
    _load_map.cache_clear()
