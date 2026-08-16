"""Selective web discovery through the existing bounded, terms-aware source adapters."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from job_finder.ai_discovery import DiscoveryCandidate
from job_finder.jobs import Job, JobOrigin
from job_finder.search_runs import SearchRunLimitError, ensure_run_allowed, execute_search_run
from job_finder.source_adapters import CancellationToken, SourceRegistry
from job_finder.source_models import (
    SearchRunRecord,
    SourceConfigRecord,
    create_search_run,
    ensure_default_sources,
)
from job_finder.sources_api import _run_response

router = APIRouter(prefix="/api", tags=["ai-discovery"])


class AiDiscoveryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_keys: list[str] = Field(min_length=1, max_length=3)
    query: str | None = Field(default=None, max_length=120)
    location: str | None = Field(default=None, max_length=120)
    limit: int = Field(default=20, ge=1, le=50)


class AiDiscoveryResponse(BaseModel):
    runs: list[dict[str, object]]
    candidates: list[DiscoveryCandidate]
    message: str


async def get_session(request: Request) -> AsyncIterator[Session]:
    with request.app.state.session_factory() as session:
        yield session


SessionDependency = Annotated[Session, Depends(get_session)]


@router.post("/ai/discovery", response_model=AiDiscoveryResponse)
async def discover_jobs(
    payload: AiDiscoveryRequest,
    request: Request,
    session: SessionDependency,
) -> AiDiscoveryResponse:
    """Run only the selected public sources; this endpoint never applies to a job."""

    ensure_default_sources(session)
    records = list(
        session.scalars(
            select(SourceConfigRecord).where(SourceConfigRecord.source_key.in_(payload.source_keys))
        )
    )
    if len(records) != len(set(payload.source_keys)):
        raise HTTPException(status_code=404, detail="Uma das fontes selecionadas não existe.")
    registry: SourceRegistry = request.app.state.source_registry
    runs: list[dict[str, object]] = []
    for source in records:
        try:
            ensure_run_allowed(session, source)
        except SearchRunLimitError as error:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
        query: dict[str, object] = {
            key: value
            for key, value in {
                "query": payload.query,
                "location": payload.location,
                "limit": payload.limit,
            }.items()
            if value is not None
        }
        run = create_search_run(session, source, query)
        session.commit()
        await execute_search_run(
            request.app.state.session_factory,
            run.id,
            registry,
            CancellationToken(),
        )
        with request.app.state.session_factory() as refreshed:
            completed = refreshed.get(SearchRunRecord, run.id)
            if completed is not None:
                runs.append(_run_response(completed).model_dump(mode="json"))

    candidates: list[DiscoveryCandidate] = []
    jobs = session.scalars(
        select(Job)
        .join(JobOrigin)
        .where(JobOrigin.source.in_(payload.source_keys))
        .order_by(Job.created_at.desc())
        .limit(payload.limit)
    )
    for job in jobs:
        origin = job.origins[0] if job.origins else None
        candidates.append(
            DiscoveryCandidate(
                title=job.title,
                company=job.company,
                location=job.location,
                url=(origin.url if origin and origin.url else job.canonical_url or ""),
                source_key=origin.source if origin else "unknown",
                evidence=f"{job.title} · {job.company}",
            )
        )
    return AiDiscoveryResponse(
        runs=runs,
        candidates=candidates,
        message=(
            "Nenhuma vaga nova encontrada nas fontes selecionadas."
            if not candidates
            else "Pesquisa concluída; revise as evidências antes de mudar o pipeline."
        ),
    )
