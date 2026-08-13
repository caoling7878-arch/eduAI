"""Serve built Vue SPAs (student + admin) with history-mode fallback."""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse


def spa_roots() -> Tuple[Path, Path]:
    here = Path(__file__).resolve().parent
    return here / "spa" / "web", here / "spa" / "admin"


def _safe_file(root: Path, rel: str) -> Optional[Path]:
    if not rel or rel.endswith("/"):
        return None
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    if candidate.is_file():
        return candidate
    return None


def _file_response(path: Path) -> FileResponse:
    headers = {}
    if path.suffix.lower() in {".html", ""}:
        headers["Cache-Control"] = "no-store, max-age=0"
        headers["Pragma"] = "no-cache"
    return FileResponse(path, headers=headers)


def mount_spas(app: FastAPI) -> None:
    """Register SPA routes. Must be called after all API routes."""
    web_dist, admin_dist = spa_roots()

    if admin_dist.is_dir() and (admin_dist / "index.html").is_file():
        admin_index = admin_dist / "index.html"

        @app.api_route("/admin", methods=["GET", "HEAD"])
        async def admin_root_redirect() -> RedirectResponse:
            return RedirectResponse(url="/admin/", status_code=307)

        @app.api_route("/admin/", methods=["GET", "HEAD"])
        async def admin_index_page() -> FileResponse:
            return _file_response(admin_index)

        @app.api_route("/admin/{full_path:path}", methods=["GET", "HEAD"])
        async def admin_spa(full_path: str) -> FileResponse:
            file = _safe_file(admin_dist, full_path)
            if file is not None:
                return _file_response(file)
            return _file_response(admin_index)

    if web_dist.is_dir() and (web_dist / "index.html").is_file():
        web_index = web_dist / "index.html"

        @app.api_route("/", methods=["GET", "HEAD"])
        async def web_index_page() -> FileResponse:
            return _file_response(web_index)

        @app.api_route("/{full_path:path}", methods=["GET", "HEAD"])
        async def web_spa(full_path: str) -> FileResponse:
            # Keep API / docs / OpenAPI for FastAPI itself.
            if full_path.startswith("api/") or full_path in {
                "docs",
                "redoc",
                "openapi.json",
            }:
                raise HTTPException(status_code=404, detail="Not Found")
            file = _safe_file(web_dist, full_path)
            if file is not None:
                return _file_response(file)
            return _file_response(web_index)
