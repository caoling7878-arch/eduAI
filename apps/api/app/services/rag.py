from __future__ import annotations

import heapq
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import KnowledgeChunk, KnowledgeDoc, LlmProvider
from .embeddings import (
    chunk_text,
    cosine,
    dumps_vec,
    embed_api,
    embed_text,
    loads_vec,
    resolve_embedding_endpoint,
    tokenize,
)
from .llm import get_default_provider

# 大库粗筛：有关键词命中时优先；候选上限避免全量 cosine
_MAX_VECTOR_CANDIDATES = 400
_BACKEND_SAMPLE = 24


def _provider_creds(db: Optional[Session]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    if db is None:
        return None, None, None
    base, key, model = resolve_embedding_endpoint()
    if base and key:
        return base, key, model
    p: Optional[LlmProvider] = get_default_provider(db)
    if not p:
        return None, None, None
    return (p.base_url or "").rstrip("/") or None, p.api_key or None, None


def index_document(db: Session, doc: KnowledgeDoc) -> dict:
    """切片并写入向量；返回切片数与后端信息。"""
    for old in list(db.scalars(select(KnowledgeChunk).where(KnowledgeChunk.doc_id == doc.id))):
        db.delete(old)
    db.flush()

    base, key, model = _provider_creds(db)
    parts = chunk_text(f"{doc.title}\n{doc.content}")
    backend_used = "hash"
    model_used = "local-hash-256"
    for i, part in enumerate(parts):
        vec, backend, mdl = embed_text(part, base_url=base, api_key=key, model=model)
        backend_used = backend
        model_used = mdl
        db.add(
            KnowledgeChunk(
                kb_id=doc.kb_id,
                doc_id=doc.id,
                chunk_index=i,
                content=part,
                embedding_json=dumps_vec(vec, backend=backend, model=mdl),
                token_count=len(tokenize(part)),
            )
        )
    doc.status = "ready"
    db.commit()
    return {"chunks": len(parts), "backend": backend_used, "model": model_used}


def reindex_kb(db: Session, kb_id: int) -> dict:
    docs = list(db.scalars(select(KnowledgeDoc).where(KnowledgeDoc.kb_id == kb_id)))
    total_chunks = 0
    backend = "hash"
    model = "local-hash-256"
    for d in docs:
        info = index_document(db, d)
        total_chunks += int(info.get("chunks") or 0)
        backend = str(info.get("backend") or backend)
        model = str(info.get("model") or model)
    return {"docs": len(docs), "chunks": total_chunks, "backend": backend, "model": model}


def embedding_status(db: Session, *, probe: bool = False) -> dict:
    base, key, model = resolve_embedding_endpoint()
    p = get_default_provider(db)
    configured = bool((base and key) or (p and p.base_url and p.api_key))
    use_base = base or ((p.base_url or "").rstrip("/") if p else None)
    use_key = key or (p.api_key if p else None)
    live_ok = False
    live_error = ""
    if probe and use_base and use_key:
        try:
            embed_api("ping", base_url=use_base, api_key=use_key, model=model, timeout=8.0)
            live_ok = True
        except Exception as e:
            live_error = str(e)[:180]
    return {
        "api_ready": configured,
        "api_live": live_ok if probe else None,
        "prefer": "api" if configured else "hash",
        "model": model if configured else "local-hash-256",
        "base_configured": bool(use_base),
        "probe_error": live_error,
        "hint": (
            "已配置 Embedding 接口；索引时优先调用，失败自动回退本地哈希。"
            if configured
            else "未配置 Embedding；当前使用本地哈希向量。可在 .env 设置 EMBEDDING_BASE_URL / EMBEDDING_API_KEY / EMBEDDING_MODEL，或后台配置 LLM Provider。"
        ),
    }


def _prefer_api_from_chunks(chunks: List[KnowledgeChunk]) -> bool:
    api_n = hash_n = 0
    for c in chunks[:_BACKEND_SAMPLE]:
        if not c.embedding_json:
            continue
        _, b, _ = loads_vec(c.embedding_json)
        if b == "api":
            api_n += 1
        else:
            hash_n += 1
    return api_n >= hash_n


def _narrow_candidates(chunks: List[KnowledgeChunk], qtok: set[str]) -> List[KnowledgeChunk]:
    """大库时先按 token 重叠粗筛，再做向量打分。"""
    if len(chunks) <= _MAX_VECTOR_CANDIDATES or not qtok:
        return chunks
    hit: List[KnowledgeChunk] = []
    miss: List[KnowledgeChunk] = []
    for c in chunks:
        ctok = set(tokenize(c.content or ""))
        if qtok & ctok:
            hit.append(c)
        else:
            miss.append(c)
    if len(hit) >= max(24, _MAX_VECTOR_CANDIDATES // 4):
        return hit[:_MAX_VECTOR_CANDIDATES]
    # 命中过少：补一批无命中切片，避免召回塌陷
    need = _MAX_VECTOR_CANDIDATES - len(hit)
    return hit + miss[:need]


def retrieve_docs(db: Session, kb_id: Optional[int], query: str, top_k: int = 3) -> List[dict]:
    if not kb_id:
        return []
    base, key, model = _provider_creds(db)
    chunks = list(db.scalars(select(KnowledgeChunk).where(KnowledgeChunk.kb_id == kb_id)))
    qtok = set(tokenize(query))
    top_k = max(1, min(int(top_k or 3), 12))

    has_vec = any(c.embedding_json for c in chunks)
    if not has_vec:
        docs = list(
            db.scalars(
                select(KnowledgeDoc).where(KnowledgeDoc.kb_id == kb_id, KnowledgeDoc.status == "ready")
            )
        )
        scored_docs = []
        for d in docs:
            dt = set(tokenize(f"{d.title}\n{d.content}"))
            score = float(len(qtok & dt) + 2 * len(qtok & set(tokenize(d.title))))
            if score > 0:
                scored_docs.append((score, d))
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        out = []
        for score, d in scored_docs[:top_k]:
            snippet = (d.content or "").strip()
            if len(snippet) > 360:
                snippet = snippet[:360] + "…"
            out.append(
                {
                    "doc_id": d.id,
                    "title": d.title,
                    "snippet": snippet,
                    "score": round(score, 4),
                    "method": "keyword",
                    "backend": "keyword",
                }
            )
        return out

    prefer_api = _prefer_api_from_chunks(chunks)
    qvec, query_backend, query_model = embed_text(
        query,
        base_url=base,
        api_key=key,
        model=model,
        prefer_api=prefer_api,
    )

    candidates = _narrow_candidates(chunks, qtok)
    # 最小堆保留 top 候选（按文档去重前多取一些）
    heap_n = max(top_k * 10, 32)
    heap: List[Tuple[float, int, KnowledgeChunk]] = []
    for c in candidates:
        vec, _, _ = loads_vec(c.embedding_json)
        if not vec or len(vec) != len(qvec):
            continue
        score = cosine(qvec, vec)
        if qtok:
            ctok = set(tokenize(c.content or ""))
            overlap = len(qtok & ctok)
            score = score + min(0.35, overlap * 0.04)
        if score <= 0.08:
            continue
        item = (score, c.id, c)
        if len(heap) < heap_n:
            heapq.heappush(heap, item)
        elif score > heap[0][0]:
            heapq.heapreplace(heap, item)

    best: dict[int, tuple] = {}
    for score, _, c in heap:
        prev = best.get(c.doc_id)
        if not prev or score > prev[0]:
            best[c.doc_id] = (score, c)

    ranked = heapq.nlargest(top_k, best.values(), key=lambda x: x[0])
    out = []
    for score, c in ranked:
        doc = db.get(KnowledgeDoc, c.doc_id)
        snippet = (c.content or "").strip()
        if len(snippet) > 360:
            snippet = snippet[:360] + "…"
        out.append(
            {
                "doc_id": c.doc_id,
                "title": doc.title if doc else f"文档#{c.doc_id}",
                "snippet": snippet,
                "score": round(float(score), 4),
                "method": "vector",
                "backend": query_backend,
                "model": query_model,
                "chunk_id": c.id,
            }
        )
    return out


def format_context(citations: List[dict]) -> str:
    if not citations:
        return ""
    blocks = []
    for i, c in enumerate(citations, 1):
        blocks.append(f"[{i}] {c['title']}\n{c['snippet']}")
    return "\n\n".join(blocks)
