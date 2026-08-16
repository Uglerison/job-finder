"""API for source settings, search runs, duplicate review and scheduling."""

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from job_finder.jobs import get_job
from job_finder.search_runs import (
    SearchRunLimitError,
    SearchTaskRegistry,
    ensure_run_allowed,
    execute_search_run,
)
from job_finder.source_adapters import (
    CancellationToken,
    SourceAdapterError,
    SourceRegistry,
    SourceSearchRequest,
)
from job_finder.source_dedup import confirm_duplicate, dismiss_duplicate
from job_finder.source_models import (
    DuplicateStatus,
    DuplicateSuggestionRecord,
    SearchRunRecord,
    SourceConfigData,
    SourceConfigRecord,
    SourceConfigResponse,
    SourceRunStatus,
    due_sources,
    ensure_default_sources,
    source_response,
)

router = APIRouter(prefix="/api", tags=["sources"])


class SourceUpdateRequest(BaseModel):
    """Editable fields for one source; source identity and secrets stay server-owned."""

    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=1, max_length=120)
    endpoint: str = Field(min_length=1, max_length=2048)
    terms_url: str | None = Field(default=None, max_length=2048)
    enabled: bool = True
    schedule_enabled: bool = False
    frequency_minutes: int = Field(default=1440, ge=15, le=10080)
    daily_limit: int = Field(default=50, ge=1, le=1000)
    per_run_limit: int = Field(default=50, ge=1, le=200)
    timeout_seconds: int = Field(default=15, ge=1, le=60)


class SearchRunRequest(BaseModel):
    """Bounded, auditable search input."""

    model_config = ConfigDict(extra="forbid")

    source_key: str = Field(min_length=2, max_length=64)
    query: str | None = Field(default=None, max_length=120)
    location: str | None = Field(default=None, max_length=120)
    limit: int | None = Field(default=None, ge=1, le=200)
    cursor: str | None = Field(default=None, max_length=255)


class SearchRunResponse(BaseModel):
    id: int
    source_key: str
    source_name: str
    status: SourceRunStatus
    query: dict[str, object]
    requested_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    duration_ms: int | None
    candidates_seen: int
    jobs_created: int
    exact_duplicates: int
    approximate_duplicates: int
    error_message: str | None
    cancellation_requested: bool
    current_cursor: str | None


class SourceTestResponse(BaseModel):
    source_key: str
    status: Literal["success", "empty", "failed", "cancelled"]
    candidates_seen: int
    duration_ms: int
    error_message: str | None = None


class DuplicateSuggestionResponse(BaseModel):
    id: int
    existing_job_id: int
    existing_job_title: str
    existing_job_company: str
    source_key: str
    candidate: dict[str, object]
    similarity: float
    reasons: list[str]
    status: str
    created_at: datetime


class SchedulerTickResponse(BaseModel):
    scheduled_source_keys: list[str]
    skipped_source_keys: list[str]


async def get_session(request: Request) -> AsyncIterator[Session]:
    session_factory: sessionmaker[Session] = request.app.state.session_factory
    with session_factory() as session:
        yield session


SessionDependency = Annotated[Session, Depends(get_session)]


def _registry(request: Request) -> SourceRegistry:
    registry = getattr(request.app.state, "source_registry", None)
    if registry is None:
        registry = SourceRegistry()
        request.app.state.source_registry = registry
    return registry


def _task_registry(request: Request) -> SearchTaskRegistry:
    tasks = getattr(request.app.state, "search_tasks", None)
    if tasks is None:
        tasks = SearchTaskRegistry()
        request.app.state.search_tasks = tasks
    return tasks


@router.get("/sources", response_model=list[SourceConfigResponse])
async def list_sources(session: SessionDependency) -> list[SourceConfigResponse]:
    """List configured sources, seeding safe defaults on first use."""

    records = ensure_default_sources(session)
    session.commit()
    return [source_response(record) for record in records]


@router.put("/sources/{source_key}", response_model=SourceConfigResponse)
async def update_source(
    source_key: str,
    payload: SourceUpdateRequest,
    session: SessionDependency,
) -> SourceConfigResponse:
    """Update limits and schedule without accepting a secret in the request body."""

    ensure_default_sources(session)
    record = session.scalar(
        select(SourceConfigRecord).where(SourceConfigRecord.source_key == source_key)
    )
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fonte não encontrada.")
    try:
        data = SourceConfigData(source_key=source_key, **payload.model_dump())
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    for key, value in data.model_dump().items():
        if key != "source_key":
            setattr(record, key, value)
    session.commit()
    session.refresh(record)
    return source_response(record)


@router.post("/sources/{source_key}/test", response_model=SourceTestResponse)
async def test_source(
    source_key: str,
    request: Request,
    session: SessionDependency,
) -> SourceTestResponse:
    """Fetch one bounded page without persisting jobs or creating a run."""

    source = _get_source(session, source_key)
    adapter = _registry(request).get(source.source_key, source.endpoint, source.timeout_seconds)
    token = CancellationToken()
    started = datetime.now().timestamp()
    try:
        result = await adapter.search(SourceSearchRequest(limit=1, cancellation=token))
    except SourceAdapterError as error:
        return SourceTestResponse(
            source_key=source_key,
            status="failed",
            candidates_seen=0,
            duration_ms=round((datetime.now().timestamp() - started) * 1000),
            error_message=str(error),
        )
    return SourceTestResponse(
        source_key=source_key,
        status="success" if result.candidates else "empty",
        candidates_seen=len(result.candidates),
        duration_ms=round((datetime.now().timestamp() - started) * 1000),
    )


@router.post("/search-runs", response_model=SearchRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_search_run(
    payload: SearchRunRequest,
    request: Request,
    session: SessionDependency,
    wait: bool = Query(default=False),
) -> SearchRunResponse:
    """Create a persisted run and execute asynchronously unless `wait=true` is requested."""

    source = _get_source(session, payload.source_key)
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
            "cursor": payload.cursor,
        }.items()
        if value is not None
    }
    from job_finder.source_models import create_search_run

    run = create_search_run(session, source, query)
    session.commit()
    registry = _registry(request)
    token = CancellationToken()
    if wait:
        await execute_search_run(request.app.state.session_factory, run.id, registry, token)
    else:
        task = asyncio.create_task(
            execute_search_run(request.app.state.session_factory, run.id, registry, token),
        )
        _task_registry(request).add(run.id, task, token)
    with request.app.state.session_factory() as refreshed_session:
        refreshed = refreshed_session.get(SearchRunRecord, run.id)
        if refreshed is None:
            raise HTTPException(status_code=500, detail="Execução não encontrada após criação.")
        return _run_response(refreshed)


@router.get("/search-runs", response_model=list[SearchRunResponse])
async def list_search_runs(
    session: SessionDependency,
    status_filter: Annotated[SourceRunStatus | None, Query(alias="status")] = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[SearchRunResponse]:
    """Return recent runs with operational counters and errors."""

    statement = select(SearchRunRecord).order_by(SearchRunRecord.requested_at.desc()).limit(limit)
    if status_filter:
        statement = statement.where(SearchRunRecord.status == status_filter)
    return [_run_response(run) for run in session.scalars(statement)]


@router.get("/search-runs/{run_id}", response_model=SearchRunResponse)
async def read_search_run(run_id: int, session: SessionDependency) -> SearchRunResponse:
    run = session.get(SearchRunRecord, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Execução não encontrada.")
    return _run_response(run)


@router.post("/search-runs/{run_id}/cancel", response_model=SearchRunResponse)
async def cancel_search_run(
    run_id: int,
    request: Request,
    session: SessionDependency,
) -> SearchRunResponse:
    """Request cancellation in both the database and the in-process token."""

    run = session.get(SearchRunRecord, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Execução não encontrada.")
    if run.status in {"pending", "running"}:
        run.cancellation_requested = True
        run.status = "cancelled" if run.status == "pending" else run.status
        session.commit()
        _task_registry(request).cancel(run_id)
    return _run_response(run)


@router.get("/duplicates", response_model=list[DuplicateSuggestionResponse])
async def list_duplicate_suggestions(
    session: SessionDependency,
    status_filter: Annotated[DuplicateStatus | None, Query(alias="status")] = "pending",
) -> list[DuplicateSuggestionResponse]:
    """List approximate matches that require explicit user confirmation."""

    statement = select(DuplicateSuggestionRecord).order_by(
        DuplicateSuggestionRecord.created_at.desc()
    )
    if status_filter:
        statement = statement.where(DuplicateSuggestionRecord.status == status_filter)
    return [_duplicate_response(session, item) for item in session.scalars(statement)]


@router.post("/duplicates/{suggestion_id}/confirm", response_model=DuplicateSuggestionResponse)
async def confirm_duplicate_suggestion(
    suggestion_id: int,
    session: SessionDependency,
) -> DuplicateSuggestionResponse:
    suggestion = session.get(DuplicateSuggestionRecord, suggestion_id)
    if suggestion is None:
        raise HTTPException(status_code=404, detail="Sugestão de duplicata não encontrada.")
    try:
        confirm_duplicate(session, suggestion)
        session.commit()
    except ValueError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(error)) from error
    return _duplicate_response(session, suggestion)


@router.post("/duplicates/{suggestion_id}/dismiss", response_model=DuplicateSuggestionResponse)
async def dismiss_duplicate_suggestion(
    suggestion_id: int,
    session: SessionDependency,
) -> DuplicateSuggestionResponse:
    suggestion = session.get(DuplicateSuggestionRecord, suggestion_id)
    if suggestion is None:
        raise HTTPException(status_code=404, detail="Sugestão de duplicata não encontrada.")
    try:
        dismiss_duplicate(session, suggestion)
        session.commit()
    except ValueError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(error)) from error
    return _duplicate_response(session, suggestion)


@router.post("/scheduler/tick", response_model=SchedulerTickResponse)
async def scheduler_tick(request: Request, session: SessionDependency) -> SchedulerTickResponse:
    """Schedule due sources without executing them when automation is disabled."""

    due = due_sources(session)
    scheduled: list[str] = []
    skipped: list[str] = []
    registry = _registry(request)
    for source in due:
        try:
            ensure_run_allowed(session, source)
        except SearchRunLimitError:
            skipped.append(source.source_key)
            continue
        from job_finder.source_models import create_search_run

        run = create_search_run(session, source, {})
        session.commit()
        token = CancellationToken()
        task = asyncio.create_task(
            execute_search_run(request.app.state.session_factory, run.id, registry, token),
        )
        _task_registry(request).add(run.id, task, token)
        scheduled.append(source.source_key)
    return SchedulerTickResponse(scheduled_source_keys=scheduled, skipped_source_keys=skipped)


def _get_source(session: Session, source_key: str) -> SourceConfigRecord:
    ensure_default_sources(session)
    source = session.scalar(
        select(SourceConfigRecord).where(SourceConfigRecord.source_key == source_key)
    )
    if source is None:
        raise HTTPException(status_code=404, detail="Fonte não encontrada.")
    return source


def _run_response(run: SearchRunRecord) -> SearchRunResponse:
    source = run.source
    return SearchRunResponse(
        id=run.id,
        source_key=source.source_key,
        source_name=source.display_name,
        status=cast(SourceRunStatus, run.status),
        query=run.query,
        requested_at=run.requested_at,
        started_at=run.started_at,
        finished_at=run.finished_at,
        duration_ms=run.duration_ms,
        candidates_seen=run.candidates_seen,
        jobs_created=run.jobs_created,
        exact_duplicates=run.exact_duplicates,
        approximate_duplicates=run.approximate_duplicates,
        error_message=run.error_message,
        cancellation_requested=run.cancellation_requested,
        current_cursor=run.current_cursor,
    )


def _duplicate_response(
    session: Session,
    suggestion: DuplicateSuggestionRecord,
) -> DuplicateSuggestionResponse:
    job = get_job(session, suggestion.existing_job_id)
    return DuplicateSuggestionResponse(
        id=suggestion.id,
        existing_job_id=suggestion.existing_job_id,
        existing_job_title=job.title if job else "Vaga removida",
        existing_job_company=job.company if job else "",
        source_key=suggestion.source_key,
        candidate=suggestion.candidate,
        similarity=suggestion.similarity,
        reasons=suggestion.reasons,
        status=suggestion.status,
        created_at=suggestion.created_at,
    )
