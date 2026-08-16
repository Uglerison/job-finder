"""Delivery of the compiled React application from the local FastAPI server."""

import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


def frontend_dist_path() -> Path:
    """Return the development location of Vite's compiled frontend assets."""

    bundle_root = getattr(sys, "_MEIPASS", None)
    if isinstance(bundle_root, str) and (Path(bundle_root) / "apps" / "web" / "dist").is_dir():
        return Path(bundle_root) / "apps" / "web" / "dist"
    return Path(__file__).resolve().parents[4] / "apps" / "web" / "dist"


def mount_frontend(application: FastAPI, dist_directory: Path) -> None:
    """Mount static assets and an SPA fallback when a compiled UI is available."""

    index_file = dist_directory / "index.html"
    if not index_file.is_file():
        return

    resolved_dist_directory = dist_directory.resolve()
    assets_directory = dist_directory / "assets"
    if assets_directory.is_dir():
        application.mount(
            "/assets",
            StaticFiles(directory=assets_directory),
            name="frontend-assets",
        )

    @application.get("/", include_in_schema=False)
    def frontend_root() -> FileResponse:
        return FileResponse(index_file)

    @application.get("/{frontend_path:path}", include_in_schema=False)
    def frontend_fallback(frontend_path: str) -> FileResponse:
        if frontend_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")

        requested_file = (dist_directory / frontend_path).resolve()
        if requested_file.is_relative_to(resolved_dist_directory) and requested_file.is_file():
            return FileResponse(requested_file)

        return FileResponse(index_file)
