from __future__ import annotations

import json
import os
import time
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import LlmProvider, LlmUsageLog, PromptTemplate, User
from .billing import consume_quota


def mask_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:3]}…{key[-4:]}"


def get_default_provider(db: Session) -> Optional[LlmProvider]:
    row = db.scalar(
        select(LlmProvider)
        .where(LlmProvider.enabled.is_(True), LlmProvider.is_default.is_(True))
        .order_by(LlmProvider.id.desc())
    )
    if row:
        return row
    return db.scalar(
        select(LlmProvider).where(LlmProvider.enabled.is_(True)).order_by(LlmProvider.id.desc())
    )


def resolve_provider_from_env() -> Tuple[Optional[str], Optional[str], str]:
    base = (
        os.getenv("LLM_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
        or os.getenv("TTS_BASE_URL")
        or ""
    ).rstrip("/")
    key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("TTS_API_KEY")
    model = os.getenv("LLM_MODEL") or "gpt-4o-mini"
    return (base or None), key, model


def get_active_prompt(db: Session, key: str, fallback: str) -> str:
    row = db.scalar(
        select(PromptTemplate)
        .where(PromptTemplate.key == key, PromptTemplate.active.is_(True))
        .order_by(PromptTemplate.version.desc())
    )
    return row.content if row and row.content.strip() else fallback


def log_usage(
    db: Session,
    *,
    user: Optional[User],
    provider_id: Optional[int],
    model: str,
    purpose: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    latency_ms: int = 0,
    success: bool = True,
    error: str = "",
) -> None:
    db.add(
        LlmUsageLog(
            user_id=user.id if user else None,
            provider_id=provider_id,
            model=model,
            purpose=purpose,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            success=success,
            error=error[:500] if error else "",
        )
    )
    if success:
        consume_quota(
            db,
            user,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            requests=1,
        )
    db.commit()


def local_reply(persona: str, user_text: str, citations: List[dict]) -> str:
    cite_note = ""
    if citations:
        titles = "、".join(c["title"] for c in citations[:3])
        cite_note = f"\n\n参考资料：{titles}"
    persona = (persona or "你是耐心的学习助手。").strip()
    return (
        f"【本地演示模式】尚未配置可用的大模型 Provider，或上游不可达。\n\n"
        f"基于人设「{persona[:40]}」，我对你的问题「{user_text[:80]}」的建议是：\n"
        f"1. 先明确已知条件与目标；\n"
        f"2. 对照知识点逐步推理；\n"
        f"3. 用一个简单例子验证结论。"
        f"{cite_note}\n\n"
        f"可在管理后台「AI 配置」填写 OpenAI 兼容 Base URL 与 API Key 后启用真实流式对话。"
    )


async def stream_chat_completion(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
) -> AsyncIterator[str]:
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": True,
    }
    async with httpx.AsyncClient(timeout=90.0) as client:
        async with client.stream("POST", url, headers=headers, json=payload) as res:
            if res.status_code >= 400:
                body = (await res.aread()).decode("utf-8", errors="ignore")
                raise RuntimeError(f"上游 {res.status_code}: {body[:240]}")
            async for line in res.aiter_lines():
                if not line:
                    continue
                if line.startswith("data:"):
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    delta = (((obj.get("choices") or [{}])[0]).get("delta") or {}).get("content")
                    if delta:
                        yield delta


async def chat_completion(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: List[Dict[str, Any]],
    temperature: float = 0.3,
    max_tokens: int = 800,
) -> str:
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        res = await client.post(url, headers=headers, json=payload)
    if res.status_code >= 400:
        raise RuntimeError(f"上游 {res.status_code}: {res.text[:240]}")
    data = res.json()
    return (((data.get("choices") or [{}])[0]).get("message") or {}).get("content") or ""


async def test_provider(base_url: str, api_key: str, model: str) -> Dict[str, Any]:
    url = f"{base_url.rstrip('/')}/chat/completions"
    t0 = time.time()
    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.post(
            url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 8,
            },
        )
    latency = int((time.time() - t0) * 1000)
    if res.status_code >= 400:
        return {"ok": False, "latency_ms": latency, "detail": res.text[:240]}
    return {"ok": True, "latency_ms": latency, "detail": "连接成功"}
