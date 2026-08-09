from __future__ import annotations

import heapq
from collections import Counter
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import KnowledgeChunk, KnowledgeDoc
from .embeddings import (
    HASH_DIM,
    chunk_text,
    cosine,
    dumps_vec,
    embed_api,
    embed_hash,
    embed_text,
    get_embedding_config,
    loads_vec,
    resolve_embedding_endpoint,
    tokenize,
)
from .llm import mask_key

# 大库粗筛：有关键词命中时优先；候选上限避免全量 cosine
_MAX_VECTOR_CANDIDATES = 400
_BACKEND_SAMPLE = 48


def _provider_creds(db: Optional[Session]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """从知识库 Embedding 配置（SiteSetting / env）解析凭证。"""
    base, key, model = resolve_embedding_endpoint(db=db)
    return base, key, model


def index_document(db: Session, doc: KnowledgeDoc) -> dict:
    """切片并写入向量；返回切片数与后端信息。"""
    for old in list(db.scalars(select(KnowledgeChunk).where(KnowledgeChunk.doc_id == doc.id))):
        db.delete(old)
    db.flush()

    cfg = get_embedding_config(db)
    prefer_api = cfg["mode"] != "hash"
    base, key, model = _provider_creds(db)
    parts = chunk_text(f"{doc.title}\n{doc.content}")
    backend_used = "hash"
    model_used = "local-hash-256"
    errors: List[str] = []
    for i, part in enumerate(parts):
        vec, backend, mdl = embed_text(
            part,
            base_url=base,
            api_key=key,
            model=model,
            prefer_api=prefer_api,
            db=db,
            last_error=errors,
        )
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
    out = {"chunks": len(parts), "backend": backend_used, "model": model_used}
    if errors and backend_used == "hash" and prefer_api:
        out["warning"] = errors[-1]
    return out


def reindex_kb(db: Session, kb_id: int) -> dict:
    docs = list(db.scalars(select(KnowledgeDoc).where(KnowledgeDoc.kb_id == kb_id)))
    total_chunks = 0
    backend = "hash"
    model = "local-hash-256"
    warning = ""
    for d in docs:
        info = index_document(db, d)
        total_chunks += int(info.get("chunks") or 0)
        backend = str(info.get("backend") or backend)
        model = str(info.get("model") or model)
        if info.get("warning"):
            warning = str(info["warning"])
    out = {"docs": len(docs), "chunks": total_chunks, "backend": backend, "model": model}
    if warning:
        out["warning"] = warning
    return out


def embedding_status(db: Session, *, probe: bool = False) -> dict:
    cfg = get_embedding_config(db)
    base, key, model = resolve_embedding_endpoint(db=db)
    mode = cfg["mode"]
    configured = bool(base and key) and mode != "hash"
    live_ok = False
    live_error = ""
    effective = "hash"
    effective_model = "local-hash-256"

    if mode == "hash":
        hint = "已强制使用本地哈希向量（256 维），检索稳定，无需外部 Embedding API。"
    elif configured:
        if probe:
            try:
                embed_api("eduai embedding probe", base_url=base or "", api_key=key or "", model=model, timeout=10.0)
                live_ok = True
                effective = "api"
                effective_model = model
                hint = f"Embedding API 连通正常（{model}）。索引与检索将使用同一向量后端。"
            except Exception as e:
                live_error = str(e)[:220]
                hint = (
                    f"已填写 Embedding 配置，但探测失败，将回退本地哈希以免检索出错。"
                    f" 错误：{live_error}。请检查 Base URL（需含 /v1）、API Key、模型是否支持 /embeddings。"
                )
        else:
            effective = "api"
            effective_model = model
            hint = "已配置 Embedding 接口；建议点击「测试连通」确认可用，并在变更后「重建向量索引」。"
    else:
        hint = (
            "未配置可用 Embedding。当前使用本地哈希向量（可离线）。"
            "若需真实语义检索，请在下方填写 OpenAI 兼容 Embedding（Base URL / API Key / 模型）。"
        )

    return {
        "mode": mode,
        "api_ready": bool(configured and (live_ok if probe else True)),
        "api_live": live_ok if probe else None,
        "prefer": effective,
        "model": effective_model if effective == "hash" else model,
        "base_url": base or "",
        "base_configured": bool(base),
        "has_key": bool(key),
        "api_key_masked": mask_key(key or ""),
        "probe_error": live_error,
        "hint": hint,
        "dim_hash": HASH_DIM,
    }


def embedding_config_public(db: Session) -> dict:
    cfg = get_embedding_config(db)
    return {
        "mode": cfg["mode"],
        "base_url": cfg["base_url"],
        "model": cfg["model"],
        "has_key": cfg["has_key"],
        "api_key_masked": mask_key(cfg["api_key"] or ""),
        "source": cfg["source"],
    }


def _chunk_profile(chunks: List[KnowledgeChunk]) -> Tuple[str, int]:
    """统计库内主导向量后端与维度，避免查询向量与索引维度不一致。"""
    dims: Counter[int] = Counter()
    backends: Counter[str] = Counter()
    for c in chunks[:_BACKEND_SAMPLE]:
        if not c.embedding_json:
            continue
        vec, b, _ = loads_vec(c.embedding_json)
        if not vec:
            continue
        dims[len(vec)] += 1
        backends[b or "hash"] += 1
    if not dims:
        return "hash", HASH_DIM
    dim = dims.most_common(1)[0][0]
    backend = backends.most_common(1)[0][0] if backends else "hash"
    return backend, dim


def _embed_query_aligned(
    db: Session,
    query: str,
    *,
    prefer_backend: str,
    expect_dim: int,
) -> Tuple[List[float], str, str]:
    """生成与索引维度一致的查询向量。"""
    base, key, model = _provider_creds(db)
    errors: List[str] = []

    if prefer_backend == "api" and expect_dim != HASH_DIM and base and key:
        try:
            vec = embed_api(query, base_url=base, api_key=key, model=model or "text-embedding-3-small")
            if len(vec) == expect_dim:
                return vec, "api", model or "text-embedding-3-small"
        except Exception as e:
            errors.append(str(e)[:160])

    # 索引是哈希，或 API 维度不匹配 / 失败 → 用哈希并对齐期望维度
    if expect_dim == HASH_DIM or prefer_backend == "hash":
        return embed_hash(query, dim=HASH_DIM), "hash", "local-hash-256"

    # 索引是 API 维，但当前 API 不可用：仍返回哈希，调用方会过滤掉不匹配维度
    vec = embed_hash(query)
    return vec, "hash", "local-hash-256"


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
    need = _MAX_VECTOR_CANDIDATES - len(hit)
    return hit + miss[:need]


def _keyword_from_chunks(chunks: List[KnowledgeChunk], query: str, top_k: int) -> List[dict]:
    qtok = set(tokenize(query))
    scored: List[Tuple[float, KnowledgeChunk]] = []
    for c in chunks:
        ctok = set(tokenize(c.content or ""))
        score = float(len(qtok & ctok))
        if score > 0:
            scored.append((score, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    out: List[dict] = []
    seen = set()
    for score, c in scored:
        if c.doc_id in seen:
            continue
        seen.add(c.doc_id)
        doc = None
        snippet = (c.content or "").strip()
        if len(snippet) > 360:
            snippet = snippet[:360] + "…"
        out.append(
            {
                "doc_id": c.doc_id,
                "title": f"文档#{c.doc_id}",
                "snippet": snippet,
                "score": round(score, 4),
                "method": "keyword",
                "backend": "keyword",
                "chunk_id": c.id,
            }
        )
        if len(out) >= top_k:
            break
    return out


def retrieve_docs(db: Session, kb_id: Optional[int], query: str, top_k: int = 3) -> List[dict]:
    if not kb_id:
        return []
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

    prefer_backend, expect_dim = _chunk_profile(chunks)
    # 与库内主导后端对齐，避免 API(1536) vs hash(256) 混用导致全零分
    if prefer_backend == "api" and _prefer_api_from_chunks(chunks):
        pass
    else:
        prefer_backend = "hash"
        expect_dim = HASH_DIM

    qvec, query_backend, query_model = _embed_query_aligned(
        db, query, prefer_backend=prefer_backend, expect_dim=expect_dim
    )

    # 查询向量维度仍对不上时，强制哈希并只打分哈希切片
    if len(qvec) != expect_dim:
        qvec = embed_hash(query)
        query_backend, query_model = "hash", "local-hash-256"
        expect_dim = HASH_DIM

    candidates = _narrow_candidates(chunks, qtok)
    heap_n = max(top_k * 10, 32)
    heap: List[Tuple[float, int, KnowledgeChunk]] = []
    matched = 0
    for c in candidates:
        vec, _, _ = loads_vec(c.embedding_json)
        if not vec or len(vec) != len(qvec):
            continue
        matched += 1
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

    # 维度错配导致无候选：降级关键词，避免「检索错误/空结果」
    if matched == 0:
        kw = _keyword_from_chunks(chunks, query, top_k)
        for item in kw:
            doc = db.get(KnowledgeDoc, item["doc_id"])
            if doc:
                item["title"] = doc.title
        return kw

    best: dict[int, tuple] = {}
    for score, _, c in heap:
        prev = best.get(c.doc_id)
        if not prev or score > prev[0]:
            best[c.doc_id] = (score, c)

    if not best:
        kw = _keyword_from_chunks(chunks, query, top_k)
        for item in kw:
            doc = db.get(KnowledgeDoc, item["doc_id"])
            if doc:
                item["title"] = doc.title
        return kw

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
