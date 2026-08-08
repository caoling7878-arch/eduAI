from __future__ import annotations

import os
from typing import Optional
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from ..services.edge_tts_service import list_preset_voices, synthesize_edge_mp3

router = APIRouter(prefix="/tts", tags=["tts"])

_NON_TTS_HOST_MARKERS = (
    "deepseek.com",
    "api.deepseek",
    "moonshot.cn",
    "bigmodel.cn",
    "dashscope.aliyuncs.com",
)


class TtsIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    """音色：female / male，或 Edge 音色名，或旧版 OpenAI 名（nova/onyx…）"""
    voice: str = Field(default="female", max_length=64)
    gender: Optional[str] = Field(default=None, max_length=16)
    lang: Optional[str] = Field(default=None, max_length=8)
    """语速微调，学习场景默认略慢：-8%"""
    rate: str = Field(default="-8%", max_length=16)
    """word=只读英文词头；sentence=整段（默认）"""
    mode: Optional[str] = Field(default=None, max_length=16)


def _looks_like_tts_endpoint(base: str) -> bool:
    host = (urlparse(base).hostname or "").lower()
    if not host:
        return False
    return not any(m in host for m in _NON_TTS_HOST_MARKERS)


def _openai_tts_config() -> tuple[Optional[str], Optional[str], str]:
    tts_base = (os.getenv("TTS_BASE_URL") or "").rstrip("/")
    tts_key = os.getenv("TTS_API_KEY") or ""
    model = os.getenv("TTS_MODEL") or "gpt-4o-mini-tts"
    if tts_base and tts_key:
        return tts_base, tts_key, model

    llm_base = (os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "").rstrip("/")
    llm_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
    if llm_base and llm_key and _looks_like_tts_endpoint(llm_base):
        return llm_base, llm_key, model
    return None, None, model


def _engine_preference() -> str:
    """auto | edge | openai。默认 auto：优先 Edge（免 Key）。"""
    return (os.getenv("TTS_ENGINE") or "auto").strip().lower()


def _edge_available() -> bool:
    if (os.getenv("TTS_EDGE_ENABLED") or "1").strip().lower() in ("0", "false", "off", "no"):
        return False
    try:
        import edge_tts  # noqa: F401
        return True
    except ImportError:
        return False


@router.get("/status")
def tts_status() -> dict:
    edge_ok = _edge_available()
    oai_base, oai_key, oai_model = _openai_tts_config()
    openai_ok = bool(oai_base and oai_key)
    pref = _engine_preference()
    available = edge_ok or openai_ok
    primary = "none"
    if pref == "openai" and openai_ok:
        primary = "openai"
    elif pref == "edge" and edge_ok:
        primary = "edge"
    elif edge_ok:
        primary = "edge"
    elif openai_ok:
        primary = "openai"

    return {
        "available": available,
        "primary": primary,
        "engines": {
            "edge": edge_ok,
            "openai": openai_ok,
        },
        "model": oai_model if openai_ok else ("edge-neural" if edge_ok else None),
        "voices": list_preset_voices() if edge_ok else [],
        "hint": (
            None
            if available
            else "请安装 edge-tts（推荐）或配置 TTS_BASE_URL + TTS_API_KEY"
        ),
    }


@router.get("/voices")
def tts_voices() -> dict:
    return {"voices": list_preset_voices(), "edge": _edge_available()}


async def _synthesize_openai(body: TtsIn) -> bytes:
    base, key, model = _openai_tts_config()
    if not base or not key:
        raise HTTPException(status_code=503, detail="未配置 OpenAI 兼容 TTS")

    # 映射性别到 OpenAI 音色
    g = (body.gender or body.voice or "female").lower()
    if g in ("male", "onyx", "echo", "fable", "ash"):
        oai_voice = "onyx" if g == "male" else (g if g in ("onyx", "echo", "fable", "ash") else "onyx")
    else:
        oai_voice = "nova" if g in ("female", "nova", "shimmer", "alloy") else (body.voice or "nova")

    payload = {
        "model": model,
        "voice": oai_voice,
        "input": body.text.strip(),
        "response_format": "mp3",
        "speed": 0.95,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.post(
            f"{base}/audio/speech",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=payload,
        )
        if res.status_code >= 400 and model != "tts-1-hd":
            payload["model"] = "tts-1-hd"
            res = await client.post(
                f"{base}/audio/speech",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=payload,
            )
        if res.status_code >= 400:
            err = (res.text or "").strip()[:200] or f"HTTP {res.status_code}"
            raise HTTPException(status_code=502, detail=f"TTS 上游失败：{err}")
    return res.content


@router.post("")
async def synthesize(body: TtsIn) -> Response:
    """
    神经 TTS：
    - 默认 Edge（微软神经音色，免 Key，支持男女声 + 句间自然停顿）
    - 可选 OpenAI 兼容 /audio/speech（需单独 Key）
    """
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="文本为空")

    pref = _engine_preference()
    edge_ok = _edge_available()
    oai_base, oai_key, _ = _openai_tts_config()
    oai_ok = bool(oai_base and oai_key)
    errors: list[str] = []

    use_order: list[str] = []
    if pref == "openai":
        use_order = ["openai", "edge"]
    elif pref == "edge":
        use_order = ["edge", "openai"]
    else:
        use_order = ["edge", "openai"]

    for eng in use_order:
        if eng == "edge" and edge_ok:
            try:
                data, meta = await synthesize_edge_mp3(
                    text,
                    gender=body.gender,
                    voice=body.voice,
                    lang=body.lang,
                    rate=body.rate or "-8%",
                    mode=body.mode,
                )
                return Response(
                    content=data,
                    media_type="audio/mpeg",
                    headers={
                        "X-TTS-Engine": meta["engine"],
                        "X-TTS-Voice": meta["voice"],
                        "X-TTS-Gender": meta["gender"],
                    },
                )
            except Exception as e:  # noqa: BLE001
                errors.append(f"edge: {e}")
                continue
        if eng == "openai" and oai_ok:
            try:
                data = await _synthesize_openai(body)
                return Response(
                    content=data,
                    media_type="audio/mpeg",
                    headers={"X-TTS-Engine": "openai", "X-TTS-Voice": body.voice or "nova"},
                )
            except HTTPException as e:
                errors.append(f"openai: {e.detail}")
                continue
            except Exception as e:  # noqa: BLE001
                errors.append(f"openai: {e}")
                continue

    if not edge_ok and not oai_ok:
        raise HTTPException(
            status_code=503,
            detail="未安装 edge-tts，且未配置 OpenAI TTS。请执行: pip install edge-tts",
        )
    raise HTTPException(
        status_code=502,
        detail="TTS 合成失败：" + ("；".join(errors)[:240] or "未知错误"),
    )
