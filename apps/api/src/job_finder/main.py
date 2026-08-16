"""FastAPI application entry point for Job Finder."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from job_finder import __version__
from job_finder.aggregated_search_api import router as aggregated_search_router
from job_finder.ai_analysis_api import router as ai_analysis_router
from job_finder.ai_cache import AnalysisPromptCache
from job_finder.ai_discovery_api import router as ai_discovery_router
from job_finder.ai_settings_api import router as ai_settings_router
from job_finder.ai_usage_api import router as ai_usage_router
from job_finder.applications_api import router as applications_router
from job_finder.dashboard_api import router as dashboard_router
from job_finder.database import create_database_engine, create_session_factory, run_migrations
from job_finder.export_api import router as export_router
from job_finder.filters_api import router as filters_router
from job_finder.frontend import frontend_dist_path, mount_frontend
from job_finder.jobs_api import router as jobs_router
from job_finder.logging import close_logging, configure_logging
from job_finder.metadata_api import router as metadata_router
from job_finder.openai_client import OpenAiResponsesClient
from job_finder.preferences_api import router as preferences_router
from job_finder.privacy_api import router as privacy_router
from job_finder.process_events_api import router as process_events_router
from job_finder.profile_api import router as profile_router
from job_finder.saved_filters_api import router as saved_filters_router
from job_finder.scheduled_searches_api import router as scheduled_searches_router
from job_finder.scheduled_searches_api import run_due_scheduled_searches
from job_finder.scheduler import PersistentScheduler
from job_finder.search_runs import SearchTaskRegistry
from job_finder.secret_store import EncryptedDatabaseVault
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
        application.state.secret_vault = EncryptedDatabaseVault(application.state.session_factory)
        application.state.scheduler = PersistentScheduler()
        with application.state.session_factory() as session:
            application.state.scheduler.recover_interrupted_runs(session)
            session.commit()
        application.state.scheduled_search_tasks = {}
        application.state.scheduled_search_worker = asyncio.create_task(
            _scheduled_search_worker(application)
        )
        yield
    finally:
        try:
            worker = getattr(application.state, "scheduled_search_worker", None)
            if worker is not None:
                worker.cancel()
                try:
                    await worker
                except asyncio.CancelledError:
                    pass
            scheduled_tasks = list(
                getattr(application.state, "scheduled_search_tasks", {}).values()
            )
            for task in scheduled_tasks:
                task.cancel()
            if scheduled_tasks:
                await asyncio.gather(*scheduled_tasks, return_exceptions=True)
            logger.info("Stopping local Job Finder service.")
            if engine is not None:
                engine.dispose()
        finally:
            close_logging(logger)


async def _scheduled_search_worker(application: FastAPI) -> None:
    """Poll persisted unified schedules while the local process is running."""

    while True:
        with application.state.session_factory() as session:
            await run_due_scheduled_searches(application, session)
        await asyncio.sleep(30)


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
    application.state.openai_client = OpenAiResponsesClient()
    application.state.analysis_prompt_cache = AnalysisPromptCache()
    application.include_router(profile_router)
    application.include_router(ai_settings_router)
    application.include_router(ai_analysis_router)
    application.include_router(ai_usage_router)
    application.include_router(dashboard_router)
    application.include_router(saved_filters_router)
    application.include_router(ai_discovery_router)
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
    application.include_router(aggregated_search_router)
    application.include_router(scheduled_searches_router)

    @application.get("/api/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", version=__version__)

    mount_frontend(application, frontend_dist_dir or frontend_dist_path())

    return application


app = create_app()
