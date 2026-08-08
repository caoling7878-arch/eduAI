from __future__ import annotations

import asyncio
import json
import time
from typing import AsyncIterator, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..db import SessionLocal, get_db
from ..models import AiAssistant, ChatMessage, ChatSession, User
from ..services.llm import (
    get_active_prompt,
    get_default_provider,
    local_reply,
    log_usage,
    stream_chat_completion,
)
from ..services.billing import check_quota
from ..services.rag import format_context, retrieve_docs

router = APIRouter(prefix="/ai/chat", tags=["ai-chat"])


class SessionIn(BaseModel):
    assistant_id: int
    title: str = "新对话"


class SessionPatch(BaseModel):
    title: str = Field(min_length=1, max_length=80)


class SessionOut(BaseModel):
    id: int
    assistant_id: int
    title: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    citations: List[dict] = Field(default_factory=list)
    created_at: Optional[str] = None


class ChatStreamIn(BaseModel):
    session_id: int
    message: str = Field(default="", max_length=4000)
    regenerate: bool = False


def _session_out(s: ChatSession) -> SessionOut:
    return SessionOut(
        id=s.id,
        assistant_id=s.assistant_id,
        title=s.title,
        created_at=s.created_at.isoformat() if s.created_at else None,
        updated_at=s.updated_at.isoformat() if s.updated_at else None,
    )


def _msg_out(m: ChatMessage) -> MessageOut:
    try:
        citations = json.loads(m.citations_json or "[]")
    except json.JSONDecodeError:
        citations = []
    return MessageOut(
        id=m.id,
        role=m.role,
        content=m.content,
        citations=citations if isinstance(citations, list) else [],
        created_at=m.created_at.isoformat() if m.created_at else None,
    )


def _parse_prompts(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(x).strip() for x in data if str(x).strip()][:6]
    except json.JSONDecodeError:
        pass
    return []


@router.get("/health")
def chat_health(db: Session = Depends(get_db)) -> dict:
    """学伴在线态：是否配置了可用 Provider。"""
    provider = get_default_provider(db)
    online = bool(provider and provider.api_key and provider.base_url)
    return {
        "online": online,
        "mode": "llm" if online else "local",
        "provider": provider.name if provider and online else None,
        "model": (provider.default_model if provider and online else None) or "local-demo",
    }


@router.get("/assistants")
def public_assistants(db: Session = Depends(get_db)) -> List[dict]:
    rows = list(
        db.scalars(select(AiAssistant).where(AiAssistant.enabled.is_(True)).order_by(AiAssistant.id))
    )
    provider = get_default_provider(db)
    online = bool(provider and provider.api_key and provider.base_url)
    return [
        {
            "id": a.id,
            "name": a.name,
            "avatar": a.avatar,
            "persona": a.persona,
            "model": a.model,
            "knowledge_base_id": a.knowledge_base_id,
            "suggested_prompts": _parse_prompts(getattr(a, "suggested_prompts", None)),
            "online": online,
            "mode": "llm" if online else "local",
        }
        for a in rows
    ]


@router.get("/sessions", response_model=List[SessionOut])
def list_sessions(
    assistant_id: Optional[int] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[SessionOut]:
    stmt = select(ChatSession).where(ChatSession.user_id == user.id).order_by(ChatSession.id.desc())
    if assistant_id:
        stmt = stmt.where(ChatSession.assistant_id == assistant_id)
    return [_session_out(s) for s in db.scalars(stmt)]


@router.post("/sessions", response_model=SessionOut)
def create_session(
    body: SessionIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SessionOut:
    a = db.get(AiAssistant, body.assistant_id)
    if not a or not a.enabled:
        raise HTTPException(status_code=404, detail="助手不可用")
    s = ChatSession(
        user_id=user.id,
        assistant_id=body.assistant_id,
        title=body.title.strip() or f"与{a.name}的对话",
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return _session_out(s)


@router.patch("/sessions/{sid}", response_model=SessionOut)
def patch_session(
    sid: int,
    body: SessionPatch,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SessionOut:
    s = db.get(ChatSession, sid)
    if not s or s.user_id != user.id:
        raise HTTPException(status_code=404, detail="会话不存在")
    s.title = body.title.strip()[:80] or s.title
    db.commit()
    db.refresh(s)
    return _session_out(s)


@router.get("/sessions/{sid}/messages", response_model=List[MessageOut])
def list_messages(
    sid: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[MessageOut]:
    s = db.get(ChatSession, sid)
    if not s or s.user_id != user.id:
        raise HTTPException(status_code=404, detail="会话不存在")
    rows = list(
        db.scalars(select(ChatMessage).where(ChatMessage.session_id == sid).order_by(ChatMessage.id))
    )
    return [_msg_out(m) for m in rows]


@router.delete("/sessions/{sid}")
def delete_session(
    sid: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    s = db.get(ChatSession, sid)
    if not s or s.user_id != user.id:
        raise HTTPException(status_code=404, detail="会话不存在")
    db.delete(s)
    db.commit()
    return {"status": "ok"}


DEFAULT_SYSTEM = (
    "你是 eduAI 平台的学习助手。请用简洁、鼓励的中文回答。"
    "若提供了参考资料，请优先依据资料作答，并在末尾用「参考：[n]」标注。"
)

DEFAULT_RAG_WRAP = (
    "以下是可参考的知识库片段：\n\n{context}\n\n"
    "请结合用户问题作答；若资料不足，请诚实说明并给出学习建议。"
)


@router.post("/stream")
async def chat_stream(
    body: ChatStreamIn,
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    """SSE 流式对话：event data JSON，最后 data: [DONE]。"""

    async def gen() -> AsyncIterator[str]:
        db = SessionLocal()
        t0 = time.time()
        provider_id = None
        model_name = "local"
        full: List[str] = []
        citations: List[dict] = []
        saved_assistant = False
        try:
            ok, quota_msg, _ = check_quota(db, user)
            if not ok:
                yield f"data: {json.dumps({'type': 'error', 'message': quota_msg, 'code': 'quota_exceeded'}, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"
                return

            s = db.get(ChatSession, body.session_id)
            if not s or s.user_id != user.id:
                yield f"data: {json.dumps({'type': 'error', 'message': '会话不存在'}, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"
                return
            assistant = db.get(AiAssistant, s.assistant_id)
            if not assistant or not assistant.enabled:
                yield f"data: {json.dumps({'type': 'error', 'message': '助手不可用'}, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"
                return

            user_text = (body.message or "").strip()

            if body.regenerate:
                hist = list(
                    db.scalars(
                        select(ChatMessage)
                        .where(ChatMessage.session_id == s.id)
                        .order_by(ChatMessage.id.desc())
                        .limit(4)
                    )
                )
                if hist and hist[0].role == "assistant":
                    db.delete(hist[0])
                    db.commit()
                    hist = hist[1:]
                if not user_text:
                    for m in hist:
                        if m.role == "user":
                            user_text = m.content
                            break
                if not user_text:
                    yield f"data: {json.dumps({'type': 'error', 'message': '没有可重新生成的消息'}, ensure_ascii=False)}\n\n"
                    yield "data: [DONE]\n\n"
                    return
            else:
                if not user_text:
                    yield f"data: {json.dumps({'type': 'error', 'message': '请输入问题'}, ensure_ascii=False)}\n\n"
                    yield "data: [DONE]\n\n"
                    return
                if s.title in ("新对话", f"与{assistant.name}的对话") and user_text:
                    s.title = user_text[:40]
                db.add(
                    ChatMessage(
                        session_id=s.id,
                        role="user",
                        content=user_text,
                        citations_json="[]",
                    )
                )
                db.commit()

            citations = retrieve_docs(db, assistant.knowledge_base_id, user_text, top_k=3)
            yield f"data: {json.dumps({'type': 'citations', 'items': citations}, ensure_ascii=False)}\n\n"

            system_tpl = (getattr(assistant, "system_prompt", None) or "").strip() or get_active_prompt(
                db, "chat_system", DEFAULT_SYSTEM
            )
            rag_tpl = get_active_prompt(db, "rag_wrap", DEFAULT_RAG_WRAP)
            system_parts = [system_tpl, f"助手人设：{assistant.persona or assistant.name}"]
            ctx = format_context(citations)
            if ctx:
                system_parts.append(rag_tpl.replace("{context}", ctx))

            history = list(
                db.scalars(
                    select(ChatMessage)
                    .where(ChatMessage.session_id == s.id)
                    .order_by(ChatMessage.id.desc())
                    .limit(16)
                )
            )
            history.reverse()
            messages = [{"role": "system", "content": "\n\n".join(system_parts)}]
            for m in history:
                if m.role in ("user", "assistant"):
                    messages.append({"role": m.role, "content": m.content})
            if not any(m.get("role") == "user" and m.get("content") == user_text for m in messages[-3:]):
                messages.append({"role": "user", "content": user_text})

            provider = get_default_provider(db)
            used_local = False

            if provider and provider.api_key and provider.base_url:
                provider_id = provider.id
                candidates = []
                for m in (assistant.model, provider.default_model):
                    if m and m not in candidates:
                        candidates.append(m)
                last_err: Optional[Exception] = None
                for model_name in candidates:
                    try:
                        async for delta in stream_chat_completion(
                            base_url=provider.base_url,
                            api_key=provider.api_key,
                            model=model_name,
                            messages=messages,
                            temperature=float(assistant.temperature or 0.7),
                        ):
                            full.append(delta)
                            yield f"data: {json.dumps({'type': 'delta', 'content': delta}, ensure_ascii=False)}\n\n"
                        last_err = None
                        break
                    except Exception as e:  # noqa: BLE001
                        last_err = e
                        full = []
                        continue
                if last_err is not None:
                    used_local = True
                    text = local_reply(assistant.persona, user_text, citations)
                    text = f"（上游暂时不可用：{str(last_err)[:80]}）\n\n{text}"
                    full = [text]
                    yield f"data: {json.dumps({'type': 'delta', 'content': text}, ensure_ascii=False)}\n\n"
                    log_usage(
                        db,
                        user=user,
                        provider_id=provider_id,
                        model=candidates[-1] if candidates else "unknown",
                        purpose="chat",
                        latency_ms=int((time.time() - t0) * 1000),
                        success=False,
                        error=str(last_err),
                    )
            else:
                used_local = True
                text = local_reply(assistant.persona, user_text, citations)
                full = [text]
                chunk = ""
                for ch in text:
                    chunk += ch
                    if len(chunk) >= 12:
                        yield f"data: {json.dumps({'type': 'delta', 'content': chunk}, ensure_ascii=False)}\n\n"
                        chunk = ""
                if chunk:
                    yield f"data: {json.dumps({'type': 'delta', 'content': chunk}, ensure_ascii=False)}\n\n"

            answer = "".join(full)
            db.add(
                ChatMessage(
                    session_id=s.id,
                    role="assistant",
                    content=answer,
                    citations_json=json.dumps(citations, ensure_ascii=False),
                )
            )
            db.commit()
            saved_assistant = True

            if not used_local or not provider:
                est_p = max(1, len(json.dumps(messages, ensure_ascii=False)) // 4)
                est_c = max(1, len(answer) // 4)
                log_usage(
                    db,
                    user=user,
                    provider_id=provider_id,
                    model=model_name if not used_local else "local-demo",
                    purpose="chat",
                    prompt_tokens=est_p,
                    completion_tokens=est_c,
                    latency_ms=int((time.time() - t0) * 1000),
                    success=True,
                )

            yield f"data: {json.dumps({'type': 'done', 'content': answer}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except (GeneratorExit, asyncio.CancelledError):
            partial = "".join(full).strip()
            if partial and not saved_assistant:
                try:
                    db.add(
                        ChatMessage(
                            session_id=body.session_id,
                            role="assistant",
                            content=partial + "\n\n（已停止生成）",
                            citations_json=json.dumps(citations, ensure_ascii=False),
                        )
                    )
                    db.commit()
                except Exception:  # noqa: BLE001
                    db.rollback()
            raise
        except Exception as e:  # noqa: BLE001
            partial = "".join(full).strip()
            if partial and not saved_assistant:
                try:
                    db.add(
                        ChatMessage(
                            session_id=body.session_id,
                            role="assistant",
                            content=partial,
                            citations_json=json.dumps(citations, ensure_ascii=False),
                        )
                    )
                    db.commit()
                except Exception:  # noqa: BLE001
                    db.rollback()
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        finally:
            db.close()

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
