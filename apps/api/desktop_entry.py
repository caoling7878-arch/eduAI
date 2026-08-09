"""Desktop / packaged entry: run uvicorn serving API + built SPAs."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _prepare_paths() -> Path:
    """Resolve app root whether running from source or PyInstaller bundle."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # onedir/onefile: bundled app package lives under _MEIPASS/app
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
        app_dir = base / "app"
        if not app_dir.is_dir():
            app_dir = base
        # Ensure importable
        if str(app_dir.parent) not in sys.path:
            sys.path.insert(0, str(app_dir.parent))
        if str(app_dir) not in sys.path:
            sys.path.insert(0, str(app_dir))
        return app_dir

    app_dir = Path(__file__).resolve().parent
    if str(app_dir) not in sys.path:
        sys.path.insert(0, str(app_dir))
    return app_dir


def main() -> None:
    _prepare_paths()

    host = os.environ.get("EDUAI_HOST", "127.0.0.1")
    port = int(os.environ.get("EDUAI_PORT", "18765"))

    # Persist SQLite under user-writable data dir when provided.
    data_dir = os.environ.get("EDUAI_DATA_DIR")
    if data_dir:
        Path(data_dir).mkdir(parents=True, exist_ok=True)
        os.environ.setdefault(
            "DATABASE_URL",
            f"sqlite:///{Path(data_dir) / 'eduai_p0.db'}",
        )

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        log_level=os.environ.get("EDUAI_LOG_LEVEL", "info"),
        access_log=False,
    )


if __name__ == "__main__":
    main()
