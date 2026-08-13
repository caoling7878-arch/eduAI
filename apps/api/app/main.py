from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .config import settings
from .db import Base, SessionLocal, engine, ensure_sqlite_columns
from .routers import (
    ai_config,
    announcements,
    analytics,
    api_tokens,
    articles,
    assistants,
    auth,
    billing,
    chat,
    checkins,
    classes,
    courses,
    datasets,
    ebooks,
    feedback,
    grading,
    knowledge,
    labs,
    learning_path,
    lti,
    math_calc,
    privacy,
    notifications,
    orders,
    papers,
    plans,
    ppt,
    practice_reco,
    progress,
    public_api,
    questions,
    reports,
    settings as settings_router,
    speech_score,
    teacher_hub,
    teachers,
    templates,
    tts,
    users,
    vocab,
    workflows,
    wrongbook,
)
from .seed import seed_ai_defaults, seed_if_empty, seed_p1_defaults
from .routers.vocab import seed_zhongkao_bank
from .routers.math_calc import seed_math_calc_bank
from .services.billing import seed_billing
from .services.workflow_engine import seed_workflow_rules

Base.metadata.create_all(bind=engine)
ensure_sqlite_columns()
with SessionLocal() as db:
    seed_if_empty(db)
    seed_ai_defaults(db)
    seed_p1_defaults(db)
    seed_zhongkao_bank(db)
    seed_math_calc_bank(db)
    seed_workflow_rules(db)
    seed_billing(db)

app = FastAPI(title=settings.app_name, version="0.9.0")
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_static_root = Path(__file__).resolve().parent / "static"
try:
    _static_root.mkdir(parents=True, exist_ok=True)
    (_static_root / "vocab").mkdir(parents=True, exist_ok=True)
except OSError:
    pass
if _static_root.is_dir():
    app.mount("/api/v1/static", StaticFiles(directory=str(_static_root)), name="static")

for mod in (
    auth,
    progress,
    tts,
    users,
    teachers,
    teacher_hub,
    courses,
    classes,
    questions,
    papers,
    announcements,
    checkins,
    plans,
    assistants,
    knowledge,
    ppt,
    orders,
    analytics,
    settings_router,
    ai_config,
    chat,
    grading,
    wrongbook,
    notifications,
    reports,
    ebooks,
    labs,
    vocab,
    math_calc,
    privacy,
    articles,
    feedback,
    templates,
    speech_score,
    practice_reco,
    datasets,
    api_tokens,
    public_api,
    learning_path,
    workflows,
    billing,
    lti,
):
    app.include_router(mod.router, prefix="/api/v1")


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.9.0"}


# Production / desktop: serve built SPAs when present (after API routes).
from .spa_serve import mount_spas  # noqa: E402

mount_spas(app)
