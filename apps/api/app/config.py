from __future__ import annotations
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "eduAI API"
    secret_key: str = "eduai-dev-secret-change-me"
    access_token_expire_minutes: int = 60 * 24 * 7
    database_url: str = f"sqlite:///{DATA_DIR / 'eduai_p0.db'}"
    cors_origins: str = (
        "http://127.0.0.1:5173,http://localhost:5173,"
        "http://127.0.0.1:5174,http://localhost:5174"
    )


settings = Settings()
