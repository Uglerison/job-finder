"""FastAPI application entry point for Job Finder."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from job_finder import __version__
from job_finder.applications_api import router as applications_router
from job_finder.database import create_database_engine, create_session_factory, run_migrations
from job_finder.export_api import router as export_router
from job_finder.filters_api import router as filters_router
from job_finder.frontend import frontend_dist_path, mount_frontend
from job_finder.jobs_api import router as jobs_router
from job_finder.logging import close_logging, configure_logging
from job_finder.metadata_api import router as metadata_router
from job_finder.preferences_api import router as preferences_router
from job_finder.privacy_api import router as privacy_router
from job_finder.process_events_api import router as process_events_router
from job_finder.profile_api import router as profile_router
from job_finder.scheduler import PersistentScheduler
from job_finder.search_runs import SearchTaskRegistry
from job_finder.settings import Settings, get_settings
from job_finder.source_adapters import SourceRegistry
from job_finder.sources_api import router as sources_router
from job_finder.trash_api import router as trash_router


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
    engine = None
    try:
        run_migrations(settings.data_dir)
        engine = create_database_engine(settings.data_dir)
        application.state.database_engine = engine
        application.state.session_factory = create_session_factory(engine)
        application.state.scheduler = PersistentScheduler()
        with application.state.session_factory() as session:
            application.state.scheduler.recover_interrupted_runs(session)
            session.commit()
        yield
    finally:
        try:
            logger.info("Stopping local Job Finder service.")
            if engine is not None:
                engine.dispose()
        finally:
            close_logging(logger)


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
    application.state.source_registry = SourceRegistry()
    application.state.search_tasks = SearchTaskRegistry()
    application.include_router(profile_router)
    application.include_router(preferences_router)
    application.include_router(filters_router)
    application.include_router(privacy_router)
    application.include_router(jobs_router)
    application.include_router(metadata_router)
    application.include_router(applications_router)
    application.include_router(process_events_router)
    application.include_router(export_router)
    application.include_router(trash_router)
    application.include_router(sources_router)

    @application.get("/api/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", version=__version__)

    mount_frontend(application, frontend_dist_dir or frontend_dist_path())

    return application


app = create_app()
