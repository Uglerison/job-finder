"""Reusable smoke verification for the local Windows application foundation."""

import json
from dataclasses import dataclass
from pathlib import Path
from urllib.request import urlopen

from job_finder import __version__
from job_finder.database import database_path
from job_finder.frontend import frontend_dist_path
from job_finder.launcher import LocalServer
from job_finder.main import create_app
from job_finder.settings import Settings


@dataclass(frozen=True)
class SmokeTestResult:
    """Evidence produced by one complete local application smoke run."""

    url: str
    health: dict[str, str]
    frontend_content: str
    database_path: Path


def run_smoke_test(
    settings: Settings,
    *,
    frontend_dist_dir: Path | None = None,
    startup_timeout_seconds: float = 10,
) -> SmokeTestResult:
    """Start, verify, persist, and stop one loopback instance of the application."""

    dist_directory = frontend_dist_dir or frontend_dist_path()
    if not (dist_directory / "index.html").is_file():
        raise RuntimeError("Compiled frontend was not found. Run the pnpm frontend build first.")

    server = LocalServer(
        create_app(settings, frontend_dist_dir=dist_directory),
        startup_timeout_seconds=startup_timeout_seconds,
    )
    try:
        server.start()
        with urlopen(f"{server.url}/api/health", timeout=2) as response:
            health = json.loads(response.read())
        with urlopen(f"{server.url}/", timeout=2) as response:
            frontend_content = response.read().decode()

        expected_health = {"status": "ok", "version": __version__}
        if health != expected_health:
            raise RuntimeError(f"Unexpected health response: {health!r}")
        if not frontend_content.strip():
            raise RuntimeError("The compiled frontend response was empty.")

        persisted_database_path = database_path(settings.data_dir)
        if not persisted_database_path.is_file():
            raise RuntimeError("SQLite persistence was not created during startup.")

        return SmokeTestResult(
            url=server.url,
            health=health,
            frontend_content=frontend_content,
            database_path=persisted_database_path,
        )
    finally:
        server.stop()
