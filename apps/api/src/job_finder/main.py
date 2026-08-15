"""FastAPI application entry point for Job Finder."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Literal

from fastapi import FastAPI
from pydantic import BaseModel

from job_finder import __version__
from job_finder.database import create_database_engine, create_session_factory, run_migrations
from job_finder.frontend import frontend_dist_path, mount_frontend
from job_finder.logging import configure_logging
from job_finder.settings import Settings, get_settings


class HealthResponse(BaseModel):
    """Minimal payload used to verify that the local service is available."""

    status: Literal["ok"]
    version: str


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Prepare and dispose local persistent resources with the server lifecycle."""

    settings: Settings = application.state.settings
    logger = configure_logging(settings)
    logger.info("Starting local Job Finder service.")
    run_migrations(settings.data_dir)
    engine = create_database_engine(settings.data_dir)
    application.state.database_engine = engine
    application.state.session_factory = create_session_factory(engine)

    try:
        yield
    finally:
        logger.info("Stopping local Job Finder service.")
        engine.dispose()


def create_app(
    settings: Settings | None = None,
    frontend_dist_dir: Path | None = None,
) -> FastAPI:
    """Create a configured application instance without starting a server."""

    application = FastAPI(
        title="Job Finder",
        version=__version__,
        docs_url="/api/docs",
        lifespan=lifespan,
        openapi_url="/api/openapi.json",
    )
    application.state.settings = settings or get_settings()

    @application.get("/api/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", version=__version__)

    mount_frontend(application, frontend_dist_dir or frontend_dist_path())

    return application


app = create_app()
