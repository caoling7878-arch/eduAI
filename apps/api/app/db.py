from __future__ import annotations
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_sqlite_columns() -> None:
    """SQLite create_all 不会 ALTER；为已有库补列。"""
    if not settings.database_url.startswith("sqlite"):
        return
    patches = {
        "lab_pages": [
            ("knowledge_points", "VARCHAR(255) DEFAULT ''"),
            ("question_ids", "VARCHAR(500) DEFAULT ''"),
        ],
        "vocab_words": [
            ("morphology_json", "TEXT DEFAULT ''"),
            ("image_key", "VARCHAR(64) DEFAULT ''"),
            ("bank", "VARCHAR(32) DEFAULT 'zhongkao_800'"),
            ("pos", "VARCHAR(64) DEFAULT ''"),
            ("scene", "VARCHAR(120) DEFAULT ''"),
            ("frequency", "VARCHAR(120) DEFAULT ''"),
            ("meanings_json", "TEXT DEFAULT '[]'"),
        ],
        "vocab_progress": [
            ("ease_step", "INTEGER DEFAULT 0"),
            ("interval_days", "INTEGER DEFAULT 0"),
            ("next_review_date", "VARCHAR(16) DEFAULT ''"),
            ("wrong_count", "INTEGER DEFAULT 0"),
            ("last_result", "VARCHAR(16) DEFAULT ''"),
        ],
        "grade_tasks": [
            ("qc_status", "VARCHAR(32) DEFAULT 'none'"),
            ("qc_note", "TEXT DEFAULT ''"),
            ("qc_by", "INTEGER"),
            ("qc_at", "DATETIME"),
        ],
        "math_calc_dailies": [
            ("elapsed_seconds", "INTEGER DEFAULT 0"),
        ],
        "users": [
            ("tenant_id", "INTEGER"),
        ],
        "ai_assistants": [
            ("system_prompt", "TEXT DEFAULT ''"),
            ("suggested_prompts", "TEXT DEFAULT '[]'"),
        ],
    }
    with engine.begin() as conn:
        for table, cols in patches.items():
            existing = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})")).fetchall()}
            for name, ddl in cols:
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
