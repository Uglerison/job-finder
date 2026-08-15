"""FastAPI application entry point for Job Finder."""

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from job_finder import __version__


class HealthResponse(BaseModel):
    """Minimal payload used to verify that the local service is available."""

    status: Literal["ok"]
    version: str


def create_app() -> FastAPI:
    """Create a configured application instance without starting a server."""

    application = FastAPI(
        title="Job Finder",
        version=__version__,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    @application.get("/api/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", version=__version__)

    return application


app = create_app()
