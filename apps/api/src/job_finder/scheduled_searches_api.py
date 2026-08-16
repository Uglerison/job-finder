"""HTTP API for local unified-search schedules and their historical results."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from datetime import datetime
from functools import partial
from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from job_finder.aggregated_search_api import _providers
from job_finder.profiles import get_current_profile_version
from job_finder.scheduled_searches import (
    ScheduledSearchJobRecord,
    ScheduledSearchRecord,
    ScheduledSearchRunRecord,
    create_scheduled_run,
    due_scheduled_searches,
    execute_scheduled_search,
    utc_now,
)
from job_finder.source_adapters import SourceRegistry

router = APIRouter(prefix="/api/scheduled-searches", tags=["scheduled-searches"])

WorkModel = Literal["all", "remote", "hybrid", "on_site"]
RunStatus = Literal["pending", "running", "completed", "partial", "failed", "cancelled"]


class ScheduledSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    query: str = Field(min_length=2, max_length=120)
    location: str | None = Field(default=None, max_length=120)
    work_model: WorkModel = "all"
    limit: int = Field(default=20, ge=1, le=100)
    frequency_minutes: int = Field(default=1440, ge=15, le=10080)
    enabled: bool = False

    @field_validator("name", "query", "location")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        return cleaned or None


class ScheduledSearchResponse(BaseModel):
    id: int
    name: str
    query: str
    location: str | None
    work_model: WorkModel
    limit: int
    frequency_minutes: int
    enabled: bool
    next_run_at: datetime | None
    last_run_at: datetime | None
    profile_version_id: int | None
    created_at: datetime
    updated_at: datetime


class ScheduledSearchRunResponse(BaseModel):
    id: int
    scheduled_search_id: int
    status: RunStatus
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
    provider_runs: list[dict[str, object]]


class ScheduledSearchJobResponse(BaseModel):
    id: int
    run_id: int
    job_id: int | None
    provider: str
    outcome: Literal["created", "exact", "approximate"]
    title: str
    company: str
    location: str | None
    url: str
    found_at: datetime


class ScheduledSearchTickResponse(BaseModel):
    scheduled_search_ids: list[int]
    run_ids: list[int]
    skipped_ids: list[int]


def get_session(request: Request) -> Iterator[Session]:
    session_factory: sessionmaker[Session] = request.app.state.session_factory
    with session_factory() as session:
        yield session


SessionDependency = Annotated[Session, Depends(get_session)]


@router.get("", response_model=list[ScheduledSearchResponse])
def list_scheduled_searches(session: SessionDependency) -> list[ScheduledSearchResponse]:
    return [
        _schedule_response(item)
        for item in session.scalars(
            select(ScheduledSearchRecord).order_by(ScheduledSearchRecord.created_at.desc())
        )
    ]


@router.post("", response_model=ScheduledSearchResponse, status_code=status.HTTP_201_CREATED)
def create_scheduled_search(
    payload: ScheduledSearchRequest,
    session: SessionDependency,
) -> ScheduledSearchResponse:
    profile = get_current_profile_version(session)
    schedule = ScheduledSearchRecord(
        name=payload.name,
        query=payload.query,
        location=payload.location,
        work_model=payload.work_model,
        limit=payload.limit,
        frequency_minutes=payload.frequency_minutes,
        enabled=payload.enabled,
        next_run_at=utc_now() if payload.enabled else None,
        profile_version_id=profile.id if profile else None,
    )
    session.add(schedule)
    session.commit()
    session.refresh(schedule)
    return _schedule_response(schedule)


@router.get("/{schedule_id}", response_model=ScheduledSearchResponse)
def read_scheduled_search(schedule_id: int, session: SessionDependency) -> ScheduledSearchResponse:
    schedule = _get_schedule(session, schedule_id)
    return _schedule_response(schedule)


@router.put("/{schedule_id}", response_model=ScheduledSearchResponse)
def update_scheduled_search(
    schedule_id: int,
    payload: ScheduledSearchRequest,
    session: SessionDependency,
) -> ScheduledSearchResponse:
    schedule = _get_schedule(session, schedule_id)
    previous_enabled = schedule.enabled
    for key, value in payload.model_dump().items():
        setattr(schedule, key, value)
    if payload.enabled and (not previous_enabled or schedule.next_run_at is None):
        schedule.next_run_at = utc_now()
    elif not payload.enabled:
        schedule.next_run_at = None
    session.commit()
    session.refresh(schedule)
    return _schedule_response(schedule)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scheduled_search(schedule_id: int, session: SessionDependency) -> None:
    schedule = _get_schedule(session, schedule_id)
    session.delete(schedule)
    session.commit()


@router.get("/{schedule_id}/runs", response_model=list[ScheduledSearchRunResponse])
def list_scheduled_search_runs(
    schedule_id: int,
    session: SessionDependency,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[ScheduledSearchRunResponse]:
    _get_schedule(session, schedule_id)
    statement = (
        select(ScheduledSearchRunRecord)
        .where(ScheduledSearchRunRecord.scheduled_search_id == schedule_id)
        .order_by(ScheduledSearchRunRecord.requested_at.desc())
        .limit(limit)
    )
    return [_run_response(run) for run in session.scalars(statement)]


@router.get("/{schedule_id}/jobs", response_model=list[ScheduledSearchJobResponse])
def list_scheduled_search_jobs(
    schedule_id: int,
    session: SessionDependency,
    run_id: int | None = Query(default=None),
    outcome: Literal["created", "exact", "approximate"] | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[ScheduledSearchJobResponse]:
    _get_schedule(session, schedule_id)
    statement = (
        select(ScheduledSearchJobRecord)
        .join(ScheduledSearchRunRecord)
        .where(ScheduledSearchRunRecord.scheduled_search_id == schedule_id)
        .order_by(ScheduledSearchJobRecord.created_at.desc())
        .limit(limit)
    )
    if run_id is not None:
        statement = statement.where(ScheduledSearchJobRecord.run_id == run_id)
    if outcome is not None:
        statement = statement.where(ScheduledSearchJobRecord.outcome == outcome)
    return [_job_response(item) for item in session.scalars(statement)]


@router.post("/tick", response_model=ScheduledSearchTickResponse)
async def tick_scheduled_searches(
    request: Request,
    session: SessionDependency,
) -> ScheduledSearchTickResponse:
    """Claim due schedules and execute them in the current local process."""

    return await run_due_scheduled_searches(request.app, session)


async def run_due_scheduled_searches(
    application: FastAPI, session: Session
) -> ScheduledSearchTickResponse:
    lock = getattr(application.state, "scheduled_search_tick_lock", None)
    if lock is None:
        lock = asyncio.Lock()
        application.state.scheduled_search_tick_lock = lock
    async with lock:
        scheduled_ids: list[int] = []
        run_ids: list[int] = []
        skipped_ids: list[int] = []
        registry: SourceRegistry = application.state.source_registry
        for schedule in due_scheduled_searches(session):
            try:
                run = create_scheduled_run(session, schedule)
                session.commit()
                scheduled_ids.append(schedule.id)
                run_ids.append(run.id)
                task = asyncio.create_task(
                    _execute_scheduled_run(application, run.id, registry),
                )
                tasks = getattr(application.state, "scheduled_search_tasks", {})
                tasks[run.id] = task
                application.state.scheduled_search_tasks = tasks
                task.add_done_callback(
                    partial(_remove_scheduled_task, run_id=run.id, task_map=tasks)
                )
            except Exception:
                session.rollback()
                skipped_ids.append(schedule.id)
    return ScheduledSearchTickResponse(
        scheduled_search_ids=scheduled_ids,
        run_ids=run_ids,
        skipped_ids=skipped_ids,
    )


async def _execute_scheduled_run(
    application: FastAPI, run_id: int, _registry: SourceRegistry
) -> None:
    providers = getattr(application.state, "aggregated_providers", None)
    if providers is None:
        with application.state.session_factory() as provider_session:
            providers = _providers(application, provider_session)
    try:
        await execute_scheduled_search(
            application.state.session_factory,
            run_id,
            providers,
            minimum_results=application.state.settings.search_minimum_results,
        )
    except Exception as error:
        with application.state.session_factory() as session:
            run = session.get(ScheduledSearchRunRecord, run_id)
            if run is not None:
                run.status = "failed"
                run.error_message = f"{type(error).__name__}: {error}"
                run.finished_at = utc_now()
                session.commit()


def _remove_scheduled_task(
    _task: asyncio.Task[object], *, run_id: int, task_map: dict[int, asyncio.Task[object]]
) -> None:
    task_map.pop(run_id, None)


def _get_schedule(session: Session, schedule_id: int) -> ScheduledSearchRecord:
    schedule = session.get(ScheduledSearchRecord, schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado.")
    return schedule


def _schedule_response(schedule: ScheduledSearchRecord) -> ScheduledSearchResponse:
    return ScheduledSearchResponse(
        id=schedule.id,
        name=schedule.name,
        query=schedule.query,
        location=schedule.location,
        work_model=cast(WorkModel, schedule.work_model),
        limit=schedule.limit,
        frequency_minutes=schedule.frequency_minutes,
        enabled=schedule.enabled,
        next_run_at=schedule.next_run_at,
        last_run_at=schedule.last_run_at,
        profile_version_id=schedule.profile_version_id,
        created_at=schedule.created_at,
        updated_at=schedule.updated_at,
    )


def _run_response(run: ScheduledSearchRunRecord) -> ScheduledSearchRunResponse:
    return ScheduledSearchRunResponse(
        id=run.id,
        scheduled_search_id=run.scheduled_search_id,
        status=cast(RunStatus, run.status),
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
        provider_runs=run.provider_runs,
    )


def _job_response(item: ScheduledSearchJobRecord) -> ScheduledSearchJobResponse:
    candidate = item.candidate
    return ScheduledSearchJobResponse(
        id=item.id,
        run_id=item.run_id,
        job_id=item.job_id,
        provider=item.provider,
        outcome=cast(Literal["created", "exact", "approximate"], item.outcome),
        title=str(candidate.get("title", "Vaga sem título")),
        company=str(candidate.get("company", "Empresa não informada")),
        location=(str(candidate["location"]) if candidate.get("location") is not None else None),
        url=str(candidate.get("url", "")),
        found_at=item.created_at,
    )
