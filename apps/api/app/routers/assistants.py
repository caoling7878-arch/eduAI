from __future__ import annotations

import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit_util import write_audit
from ..db import get_db
from ..models import AiAssistant, User
from ..rbac import require_staff
from ..schemas import AssistantIn, AssistantOut

router = APIRouter(prefix="/assistants", tags=["assistants"])


def _parse_prompts(raw: str | None) -> List[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(x).strip() for x in data if str(x).strip()][:8]
    except json.JSONDecodeError:
        pass
    return []


def assistant_out(a: AiAssistant) -> AssistantOut:
    return AssistantOut(
        id=a.id,
        name=a.name,
        avatar=a.avatar,
        persona=a.persona or "",
        system_prompt=getattr(a, "system_prompt", None) or "",
        suggested_prompts=_parse_prompts(getattr(a, "suggested_prompts", None)),
        model=a.model,
        temperature=float(a.temperature or 0.7),
        knowledge_base_id=a.knowledge_base_id,
        enabled=bool(a.enabled),
    )


def _dump_in(body: AssistantIn) -> dict:
    data = body.model_dump()
    prompts = data.pop("suggested_prompts", []) or []
    data["suggested_prompts"] = json.dumps(
        [str(x).strip() for x in prompts if str(x).strip()][:8],
        ensure_ascii=False,
    )
    return data


@router.get("", response_model=list[AssistantOut])
def list_assistants(db: Session = Depends(get_db)) -> list[AssistantOut]:
    return [assistant_out(a) for a in db.scalars(select(AiAssistant).order_by(AiAssistant.id))]


@router.post("", response_model=AssistantOut)
def create_assistant(
    body: AssistantIn,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> AssistantOut:
    a = AiAssistant(**_dump_in(body))
    db.add(a)
    write_audit(db, user=admin, action="assistant.create", resource=body.name)
    db.commit()
    db.refresh(a)
    return assistant_out(a)


@router.patch("/{aid}", response_model=AssistantOut)
def update_assistant(
    aid: int,
    body: AssistantIn,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> AssistantOut:
    a = db.get(AiAssistant, aid)
    if not a:
        raise HTTPException(status_code=404, detail="助手不存在")
    for k, v in _dump_in(body).items():
        setattr(a, k, v)
    write_audit(db, user=admin, action="assistant.update", resource=str(aid))
    db.commit()
    db.refresh(a)
    return assistant_out(a)


@router.delete("/{aid}")
def delete_assistant(
    aid: int,
    admin: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    a = db.get(AiAssistant, aid)
    if not a:
        raise HTTPException(status_code=404, detail="助手不存在")
    db.delete(a)
    write_audit(db, user=admin, action="assistant.delete", resource=str(aid))
    db.commit()
    return {"status": "ok"}
