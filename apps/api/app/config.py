from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]


def _resolve_data_dir() -> Path:
    env = os.environ.get("EDUAI_DATA_DIR")
    if env:
        path = Path(env)
    else:
        path = ROOT / "data"
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        # Packaged read-only tree: fall back to user home.
        path = Path.home() / ".eduai" / "data"
        path.mkdir(parents=True, exist_ok=True)
    return path


DATA_DIR = _resolve_data_dir()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "eduAI API"
    secret_key: str = "eduai-dev-secret-change-me"
    access_token_expire_minutes: int = 60 * 24 * 7
    database_url: str = f"sqlite:///{DATA_DIR / 'eduai_p0.db'}"
    cors_origins: str = (
        "http://127.0.0.1:5173,http://localhost:5173,"
        "http://127.0.0.1:5174,http://localhost:5174,"
        "http://127.0.0.1:18765,http://localhost:18765,"
        "app://.,null"
    )


settings = Settings()
