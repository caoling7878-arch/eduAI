from __future__ import annotations

import json
import os
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..audit_util import write_audit
from ..db import get_db
from ..models import LlmProvider, LlmUsageLog, PromptTemplate, SiteSetting, User
from ..rbac import require_admin, require_staff
from ..services.llm import mask_key, resolve_provider_from_env, test_provider

router = APIRouter(prefix="/ai", tags=["ai-config"])


class ProviderIn(BaseModel):
    name: str
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    default_model: str = "gpt-4o-mini"
    enabled: bool = True
    is_default: bool = False


class ProviderOut(BaseModel):
    id: int
    name: str
    base_url: str
    api_key_masked: str
    has_key: bool
    default_model: str
    enabled: bool
    is_default: bool

    model_config = {"from_attributes": True}


class PromptIn(BaseModel):
    key: str = Field(min_length=1, max_length=64)
    name: str
    content: str = ""
    active: bool = True


class PromptOut(BaseModel):
    id: int
    key: str
    name: str
    content: str
    version: int
    active: bool

    model_config = {"from_attributes": True}


class UsageOut(BaseModel):
    id: int
    user_id: Optional[int]
    provider_id: Optional[int]
    model: str
    purpose: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    success: bool
    error: str
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}

    @field_validator("created_at", mode="before")
    @classmethod
    def _fmt_created_at(cls, v: object) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, datetime):
            return v.isoformat()
        return str(v)


class UsageSummary(BaseModel):
    total_calls: int
    success_calls: int
    fail_calls: int
    prompt_tokens: int
    completion_tokens: int
    avg_latency_ms: int


def _provider_out(p: LlmProvider) -> ProviderOut:
    return ProviderOut(
        id=p.id,
        name=p.name,
        base_url=p.base_url,
        api_key_masked=mask_key(p.api_key),
        has_key=bool(p.api_key),
        default_model=p.default_model,
        enabled=p.enabled,
        is_default=p.is_default,
    )


@router.get("/providers", response_model=List[ProviderOut])
def list_providers(_: User = Depends(require_staff), db: Session = Depends(get_db)) -> List[ProviderOut]:
    rows = list(db.scalars(select(LlmProvider).order_by(LlmProvider.id.desc())))
    return [_provider_out(r) for r in rows]


@router.post("/providers", response_model=ProviderOut)
def create_provider(
    body: ProviderIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ProviderOut:
    if body.is_default:
        for p in db.scalars(select(LlmProvider)):
            p.is_default = False
    row = LlmProvider(**body.model_dump())
    db.add(row)
    write_audit(db, user=admin, action="ai.provider.create", resource=body.name)
    db.commit()
    db.refresh(row)
    return _provider_out(row)


@router.patch("/providers/{pid}", response_model=ProviderOut)
def update_provider(
    pid: int,
    body: ProviderIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ProviderOut:
    row = db.get(LlmProvider, pid)
    if not row:
        raise HTTPException(status_code=404, detail="Provider 不存在")
    if body.is_default:
        for p in db.scalars(select(LlmProvider)):
            p.is_default = False
    data = body.model_dump()
    # 留空 api_key 表示不覆盖原密钥
    if not data.get("api_key"):
        data.pop("api_key", None)
    for k, v in data.items():
        setattr(row, k, v)
    write_audit(db, user=admin, action="ai.provider.update", resource=str(pid))
    db.commit()
    db.refresh(row)
    return _provider_out(row)


@router.delete("/providers/{pid}")
def delete_provider(
    pid: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    row = db.get(LlmProvider, pid)
    if not row:
        raise HTTPException(status_code=404, detail="Provider 不存在")
    db.delete(row)
    write_audit(db, user=admin, action="ai.provider.delete", resource=str(pid))
    db.commit()
    return {"status": "ok"}


@router.post("/providers/{pid}/test")
async def test_provider_api(
    pid: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    row = db.get(LlmProvider, pid)
    if not row:
        raise HTTPException(status_code=404, detail="Provider 不存在")
    if not row.api_key:
        raise HTTPException(status_code=400, detail="未配置 API Key")
    return await test_provider(row.base_url, row.api_key, row.default_model)


@router.post("/providers/import-env", response_model=ProviderOut)
def import_from_env(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ProviderOut:
    base, key, model = resolve_provider_from_env()
    if not base or not key:
        raise HTTPException(status_code=400, detail="环境变量未配置 LLM_BASE_URL / LLM_API_KEY")
    for p in db.scalars(select(LlmProvider)):
        p.is_default = False
    row = LlmProvider(
        name=os.getenv("LLM_PROVIDER_NAME") or "环境变量导入",
        base_url=base,
        api_key=key,
        default_model=model,
        enabled=True,
        is_default=True,
    )
    db.add(row)
    write_audit(db, user=admin, action="ai.provider.import_env", resource=row.name)
    db.commit()
    db.refresh(row)
    return _provider_out(row)


@router.get("/prompts", response_model=List[PromptOut])
def list_prompts(_: User = Depends(require_staff), db: Session = Depends(get_db)) -> List[PromptTemplate]:
    return list(db.scalars(select(PromptTemplate).order_by(PromptTemplate.key, PromptTemplate.version.desc())))


@router.post("/prompts", response_model=PromptOut)
def create_prompt(
    body: PromptIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PromptTemplate:
    latest = db.scalar(
        select(func.max(PromptTemplate.version)).where(PromptTemplate.key == body.key)
    )
    version = int(latest or 0) + 1
    if body.active:
        for p in db.scalars(select(PromptTemplate).where(PromptTemplate.key == body.key)):
            p.active = False
    row = PromptTemplate(
        key=body.key,
        name=body.name,
        content=body.content,
        version=version,
        active=body.active,
    )
    db.add(row)
    write_audit(db, user=admin, action="ai.prompt.create", resource=body.key)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/prompts/{pid}", response_model=PromptOut)
def update_prompt(
    pid: int,
    body: PromptIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PromptTemplate:
    row = db.get(PromptTemplate, pid)
    if not row:
        raise HTTPException(status_code=404, detail="Prompt 不存在")
    if body.active:
        for p in db.scalars(select(PromptTemplate).where(PromptTemplate.key == body.key)):
            if p.id != pid:
                p.active = False
    row.key = body.key
    row.name = body.name
    row.content = body.content
    row.active = body.active
    write_audit(db, user=admin, action="ai.prompt.update", resource=str(pid))
    db.commit()
    db.refresh(row)
    return row


@router.get("/usage", response_model=List[UsageOut])
def list_usage(_: User = Depends(require_staff), db: Session = Depends(get_db)) -> List[LlmUsageLog]:
    return list(db.scalars(select(LlmUsageLog).order_by(LlmUsageLog.id.desc()).limit(100)))


@router.get("/usage/summary", response_model=UsageSummary)
def usage_summary(_: User = Depends(require_staff), db: Session = Depends(get_db)) -> UsageSummary:
    rows = list(db.scalars(select(LlmUsageLog)))
    total = len(rows)
    ok = sum(1 for r in rows if r.success)
    pt = sum(r.prompt_tokens for r in rows)
    ct = sum(r.completion_tokens for r in rows)
    avg = int(sum(r.latency_ms for r in rows) / total) if total else 0
    return UsageSummary(
        total_calls=total,
        success_calls=ok,
        fail_calls=total - ok,
        prompt_tokens=pt,
        completion_tokens=ct,
        avg_latency_ms=avg,
    )


# 粗估单价：USD / 1K tokens（演示用，可被 SiteSetting llm_price_json 覆盖）
_MODEL_PRICE = {
    "gpt-4o-mini": (0.00015, 0.0006),
    "gpt-4o": (0.0025, 0.01),
    "deepseek-chat": (0.00014, 0.00028),
    "deepseek-v4-pro": (0.0005, 0.002),
    "local-demo": (0.0, 0.0),
    "local-grade": (0.0, 0.0),
}


def _load_price_map(db: Session) -> dict:
    prices = dict(_MODEL_PRICE)
    row = db.scalar(select(SiteSetting).where(SiteSetting.key == "llm_price_json"))
    if row and row.value:
        try:
            data = json.loads(row.value)
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, (list, tuple)) and len(v) >= 2:
                        prices[str(k).lower()] = (float(v[0]), float(v[1]))
                    elif isinstance(v, dict):
                        prices[str(k).lower()] = (
                            float(v.get("in", v.get("prompt", 0.0002))),
                            float(v.get("out", v.get("completion", 0.0008))),
                        )
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    return prices


def _price_for(model: str, price_map: dict) -> tuple:
    m = (model or "").lower()
    for k, v in price_map.items():
        if k in m:
            return v
    return (0.0002, 0.0008)


class CostPriceIn(BaseModel):
    prices: dict = Field(
        default_factory=dict,
        description='模型单价，如 {"gpt-4o-mini":{"in":0.00015,"out":0.0006}}',
    )


@router.get("/usage/cost")
def usage_cost(
    days: int = Query(default=0, ge=0, le=365, description="近 N 天，0=全部"),
    _: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> dict:
    rows = list(db.scalars(select(LlmUsageLog)))
    if days > 0:
        from datetime import datetime, timedelta, timezone

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        filtered = []
        for r in rows:
            if not r.created_at:
                continue
            ts = r.created_at
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts >= cutoff:
                filtered.append(r)
        rows = filtered

    price_map = _load_price_map(db)
    by_model: dict = {}
    by_day: dict = {}
    by_purpose: dict = {}
    total_cost = 0.0
    for r in rows:
        pin, pout = _price_for(r.model, price_map)
        cost = (r.prompt_tokens / 1000.0) * pin + (r.completion_tokens / 1000.0) * pout
        total_cost += cost
        bm = by_model.setdefault(
            r.model or "unknown",
            {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0},
        )
        bm["calls"] += 1
        bm["prompt_tokens"] += r.prompt_tokens
        bm["completion_tokens"] += r.completion_tokens
        bm["cost_usd"] = round(bm["cost_usd"] + cost, 6)
        day = r.created_at.date().isoformat() if r.created_at else "unknown"
        bd = by_day.setdefault(day, {"calls": 0, "cost_usd": 0.0})
        bd["calls"] += 1
        bd["cost_usd"] = round(bd["cost_usd"] + cost, 6)
        bp = by_purpose.setdefault(r.purpose or "other", {"calls": 0, "cost_usd": 0.0})
        bp["calls"] += 1
        bp["cost_usd"] = round(bp["cost_usd"] + cost, 6)

    return {
        "total_cost_usd": round(total_cost, 6),
        "days": days or None,
        "by_model": by_model,
        "by_day": dict(sorted(by_day.items())),
        "by_purpose": by_purpose,
        "price_table": {k: {"in": v[0], "out": v[1]} for k, v in sorted(price_map.items())},
        "note": "成本为可配置单价估算，非账单金额；可在本页保存单价或导出 CSV",
    }


@router.put("/usage/cost/prices")
def save_cost_prices(
    body: CostPriceIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    row = db.scalar(select(SiteSetting).where(SiteSetting.key == "llm_price_json"))
    payload = json.dumps(body.prices, ensure_ascii=False)
    if row:
        row.value = payload
    else:
        db.add(SiteSetting(key="llm_price_json", value=payload))
    write_audit(db, user=admin, action="ai.cost_prices", resource="llm_price_json")
    db.commit()
    return {"status": "ok"}


@router.get("/usage/cost/export")
def export_cost_csv(
    days: int = Query(default=0, ge=0, le=365),
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    import csv
    import io

    from fastapi.responses import StreamingResponse

    data = usage_cost(days=days, _=user, db=db)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["section", "key", "calls", "prompt_tokens", "completion_tokens", "cost_usd"])
    w.writerow(["total", "all", "", "", "", data["total_cost_usd"]])
    for k, v in data["by_model"].items():
        w.writerow(
            ["model", k, v["calls"], v.get("prompt_tokens", ""), v.get("completion_tokens", ""), v["cost_usd"]]
        )
    for k, v in data["by_purpose"].items():
        w.writerow(["purpose", k, v["calls"], "", "", v["cost_usd"]])
    for k, v in data["by_day"].items():
        w.writerow(["day", k, v["calls"], "", "", v["cost_usd"]])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=llm-cost.csv"},
    )

