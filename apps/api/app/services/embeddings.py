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

HASH_DIM = 256


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


def resolve_embedding_endpoint(
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str], str]:
    base = (
        (base_url or "").rstrip("/")
        or (os.getenv("EMBEDDING_BASE_URL") or "").rstrip("/")
        or (os.getenv("LLM_BASE_URL") or "").rstrip("/")
        or (os.getenv("OPENAI_BASE_URL") or "").rstrip("/")
    )
    key = (
        api_key
        or os.getenv("EMBEDDING_API_KEY")
        or os.getenv("LLM_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or ""
    )
    mdl = (
        model
        or os.getenv("EMBEDDING_MODEL")
        or "text-embedding-3-small"
    )
    return (base or None), (key or None), mdl


def embed_api(
    text: str,
    *,
    base_url: str,
    api_key: str,
    model: str,
    timeout: float = 30.0,
) -> List[float]:
    url = f"{base_url.rstrip('/')}/embeddings"
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
) -> Tuple[List[float], str, str]:
    """
    返回 (vector, backend, model_name)。
    backend: api | hash
    """
    if prefer_api:
        base, key, mdl = resolve_embedding_endpoint(base_url, api_key, model)
        if base and key:
            try:
                vec = embed_api(text, base_url=base, api_key=key, model=mdl)
                return vec, "api", mdl
            except Exception:
                pass
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


# 兼容旧调用：仅返回向量
def embed_text_legacy(text: str) -> List[float]:
    vec, _, _ = embed_text(text)
    return vec


# 别名：历史代码使用 DIM
DIM = HASH_DIM
