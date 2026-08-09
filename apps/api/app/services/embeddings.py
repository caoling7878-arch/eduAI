"""文本向量：优先 OpenAI 兼容 Embedding API，失败回退本地哈希向量。"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

HASH_DIM = 256
DIM = HASH_DIM  # 历史别名

SETTING_BASE = "embedding.base_url"
SETTING_KEY = "embedding.api_key"
SETTING_MODEL = "embedding.model"
SETTING_MODE = "embedding.mode"  # auto | api | hash


def tokenize(text: str) -> List[str]:
    raw = (text or "").lower()
    parts = re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]+", raw)
    out: List[str] = []
    for p in parts:
        if re.fullmatch(r"[\u4e00-\u9fff]+", p):
            if len(p) >= 2:
                out.append(p)
            for n in (2, 3):
                if len(p) >= n:
                    for i in range(len(p) - n + 1):
                        out.append(p[i : i + n])
        elif len(p) >= 2:
            out.append(p)
    return out


def _hash_bucket(token: str, dim: int = HASH_DIM) -> int:
    h = hashlib.md5(token.encode("utf-8")).hexdigest()
    return int(h[:8], 16) % dim


def embed_hash(text: str, dim: int = HASH_DIM) -> List[float]:
    """特征哈希 + TF 归一化，无外部依赖。"""
    tokens = tokenize(text)
    if not tokens:
        return [0.0] * dim
    counts = Counter(tokens)
    vec = [0.0] * dim
    for tok, c in counts.items():
        idx = _hash_bucket(tok, dim)
        sign = 1.0 if int(hashlib.md5((tok + "#").encode()).hexdigest()[:2], 16) % 2 == 0 else -1.0
        vec[idx] += sign * (1.0 + math.log(c))
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _site_map(db: Optional[Session]) -> Dict[str, str]:
    if db is None:
        return {}
    from ..models import SiteSetting

    rows = list(db.scalars(select(SiteSetting).where(SiteSetting.key.like("embedding.%"))))
    return {r.key: (r.value or "") for r in rows}


def get_embedding_config(db: Optional[Session] = None) -> Dict[str, Any]:
    """合并 SiteSetting → 环境变量后的有效配置（不含探测）。"""
    site = _site_map(db)
    # 默认 hash：避免把仅支持对话的 LLM 地址误当作 Embedding，导致检索维度错配
    mode = (site.get(SETTING_MODE) or os.getenv("EMBEDDING_MODE") or "hash").strip().lower()
    if mode not in ("auto", "api", "hash"):
        mode = "hash"

    base = (
        (site.get(SETTING_BASE) or "").rstrip("/")
        or (os.getenv("EMBEDDING_BASE_URL") or "").rstrip("/")
        or (os.getenv("LLM_BASE_URL") or "").rstrip("/")
        or (os.getenv("OPENAI_BASE_URL") or "").rstrip("/")
    )
    key = (
        site.get(SETTING_KEY)
        or os.getenv("EMBEDDING_API_KEY")
        or os.getenv("LLM_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or ""
    )
    model = (
        (site.get(SETTING_MODEL) or "").strip()
        or (os.getenv("EMBEDDING_MODEL") or "").strip()
        or "text-embedding-3-small"
    )
    return {
        "mode": mode,
        "base_url": base,
        "api_key": key,
        "model": model,
        "has_key": bool(key),
        "source": "site" if site.get(SETTING_BASE) or site.get(SETTING_MODE) else "env",
    }


def save_embedding_config(
    db: Session,
    *,
    mode: str = "auto",
    base_url: str = "",
    api_key: Optional[str] = None,
    model: str = "text-embedding-3-small",
) -> Dict[str, Any]:
    from ..models import SiteSetting

    mode = (mode or "auto").strip().lower()
    if mode not in ("auto", "api", "hash"):
        mode = "auto"

    def upsert(k: str, v: str) -> None:
        row = db.scalar(select(SiteSetting).where(SiteSetting.key == k))
        if row is None:
            db.add(SiteSetting(key=k, value=v))
        else:
            row.value = v

    upsert(SETTING_MODE, mode)
    upsert(SETTING_BASE, (base_url or "").rstrip("/"))
    upsert(SETTING_MODEL, (model or "text-embedding-3-small").strip())
    # api_key=None 表示不改；空字符串表示清空
    if api_key is not None:
        upsert(SETTING_KEY, api_key)
    db.commit()
    return get_embedding_config(db)


def resolve_embedding_endpoint(
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    db: Optional[Session] = None,
) -> Tuple[Optional[str], Optional[str], str]:
    cfg = get_embedding_config(db)
    if cfg["mode"] == "hash":
        return None, None, "local-hash-256"
    base = (base_url or "").rstrip("/") or cfg["base_url"] or None
    key = api_key if api_key is not None and api_key != "" else (cfg["api_key"] or None)
    if api_key == "":
        key = None
    mdl = model or cfg["model"] or "text-embedding-3-small"
    if cfg["mode"] == "api" and (not base or not key):
        # 强制 API 但未配齐时仍返回空，由调用方回退
        return base, key, mdl
    return (base or None), (key or None), mdl


def embed_api(
    text: str,
    *,
    base_url: str,
    api_key: str,
    model: str,
    timeout: float = 30.0,
) -> List[float]:
    root = base_url.rstrip("/")
    # 兼容用户填了不带 /v1 的根地址
    if root.endswith("/embeddings"):
        url = root
    else:
        url = f"{root}/embeddings"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "input": (text or "")[:8000]}
    with httpx.Client(timeout=timeout) as client:
        res = client.post(url, headers=headers, json=payload)
        res.raise_for_status()
        data = res.json()
    items = data.get("data") or []
    if not items:
        raise ValueError("embedding API 返回空")
    vec = items[0].get("embedding")
    if not isinstance(vec, list) or not vec:
        raise ValueError("embedding 格式无效")
    floats = [float(x) for x in vec]
    norm = math.sqrt(sum(v * v for v in floats)) or 1.0
    return [v / norm for v in floats]


def embed_text(
    text: str,
    *,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    prefer_api: bool = True,
    db: Optional[Session] = None,
    last_error: Optional[List[str]] = None,
) -> Tuple[List[float], str, str]:
    """
    返回 (vector, backend, model_name)。
    backend: api | hash
    """
    if prefer_api:
        base, key, mdl = resolve_embedding_endpoint(base_url, api_key, model, db=db)
        if base and key:
            try:
                vec = embed_api(text, base_url=base, api_key=key, model=mdl)
                return vec, "api", mdl
            except Exception as e:
                if last_error is not None:
                    last_error.append(str(e)[:200])
    vec = embed_hash(text)
    return vec, "hash", "local-hash-256"


def cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return float(sum(x * y for x, y in zip(a, b)))


def chunk_text(text: str, max_chars: int = 420, overlap: int = 60) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]
    chunks: List[str] = []
    i = 0
    while i < len(text):
        end = min(len(text), i + max_chars)
        slice_ = text[i:end]
        for sep in ("。", "！", "？", "\n", ".", "!", "?"):
            pos = slice_.rfind(sep)
            if pos > max_chars * 0.4:
                end = i + pos + 1
                slice_ = text[i:end]
                break
        chunks.append(slice_.strip())
        if end >= len(text):
            break
        i = max(end - overlap, i + 1)
    return [c for c in chunks if c]


def dumps_vec(vec: List[float], *, backend: str = "hash", model: str = "") -> str:
    payload: Dict[str, Any] = {
        "backend": backend,
        "model": model,
        "dim": len(vec),
        "v": [round(v, 6) for v in vec],
    }
    return json.dumps(payload, ensure_ascii=False)


def loads_vec(raw: str) -> Tuple[List[float], str, str]:
    """兼容旧版纯数组与新版 {backend,model,dim,v}。"""
    try:
        data = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return [], "hash", ""
    if isinstance(data, dict) and isinstance(data.get("v"), list):
        vec = [float(x) for x in data["v"]]
        return vec, str(data.get("backend") or "hash"), str(data.get("model") or "")
    if isinstance(data, list) and data:
        return [float(x) for x in data], "hash", "local-hash-256"
    return [], "hash", ""


def embed_text_legacy(text: str) -> List[float]:
    vec, _, _ = embed_text(text)
    return vec
