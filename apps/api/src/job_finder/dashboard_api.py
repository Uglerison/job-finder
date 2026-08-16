"""Read-only dashboard metrics assembled from the local event history."""

from collections.abc import Iterator
from datetime import date, datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from job_finder.applications import Application, ApplicationEvent
from job_finder.dashboard_metrics import (
    DashboardFilters,
    MetricAgendaEvent,
    MetricApplication,
    MetricApplicationEvent,
    MetricJob,
    MetricSearchRun,
    _timezone,
    build_dashboard,
)
from job_finder.jobs import Job, JobOrigin
from job_finder.process_events import ProcessEvent
from job_finder.search_runs import SearchRunRecord

router = APIRouter(prefix="/api", tags=["dashboard"])


class DashboardPeriodResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_: str
    to: str
    timezone: str
    source_key: str | None


class DashboardCardsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jobs_found: int
    applications: int
    interviews: int
    offers: int
    hired: int
    rejected: int
    active_pipeline: int


class DashboardFunnelResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    label: str
    count: int
    denominator: int
    conversion_percent: float | None


class DashboardSeriesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period_start: str
    jobs: int
    applications: int
    interviews: int


class DashboardSourceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_key: str
    jobs: int
    applications: int
    interviews: int
    errors: int
    application_rate_percent: float | None


class DashboardAgendaResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    upcoming: int
    overdue: int


class DashboardResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period: DashboardPeriodResponse
    cards: DashboardCardsResponse
    funnel: list[DashboardFunnelResponse]
    series: list[DashboardSeriesResponse]
    sources: list[DashboardSourceResponse]
    agenda: DashboardAgendaResponse


def get_session(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        yield session


SessionDependency = Annotated[Session, Depends(get_session)]


@router.get("/dashboard/summary", response_model=DashboardResponse)
def read_dashboard_summary(
    session: SessionDependency,
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
    timezone_name: Annotated[str, Query(alias="timezone")] = "America/Sao_Paulo",
    source_key: str | None = None,
) -> DashboardResponse:
    """Return cards, funnel, weekly series and source performance for a bounded period."""

    try:
        timezone_info = _timezone(timezone_name)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    today = datetime.now(timezone_info).date()
    start_date = from_date or (today - timedelta(days=30))
    end_date = to_date or today
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A data final deve ser igual ou posterior à data inicial.",
        )
    start_at = datetime.combine(
        start_date,
        datetime.min.time(),
        tzinfo=timezone_info,
    ).astimezone(timezone.utc)
    end_at = datetime.combine(
        end_date + timedelta(days=1),
        datetime.min.time(),
        tzinfo=timezone_info,
    ).astimezone(timezone.utc)

    jobs = list(session.scalars(select(Job)))
    origins_by_job: dict[int, list[str]] = {}
    for origin in session.scalars(select(JobOrigin).order_by(JobOrigin.id)):
        origins_by_job.setdefault(origin.job_id, []).append(origin.source)
    applications = list(session.scalars(select(Application)))
    application_events = list(
        session.scalars(select(ApplicationEvent).order_by(ApplicationEvent.sequence_number))
    )
    events_by_application: dict[int, list[MetricApplicationEvent]] = {}
    for event in application_events:
        events_by_application.setdefault(event.application_id, []).append(
            MetricApplicationEvent(event.to_status, event.occurred_at)
        )
    runs = list(session.scalars(select(SearchRunRecord)))
    process_events = list(session.scalars(select(ProcessEvent)))
    result = build_dashboard(
        [
            MetricJob(job.id, job.created_at, tuple(origins_by_job.get(job.id, [])), job.deleted_at)
            for job in jobs
        ],
        [
            MetricApplication(
                application.job_id,
                application.created_at,
                application.current_status,
                tuple(events_by_application.get(application.id, [])),
            )
            for application in applications
        ],
        [
            MetricSearchRun(
                run.source.source_key,
                run.requested_at,
                run.status,
                run.jobs_created,
                run.error_message,
            )
            for run in runs
        ],
        [
            MetricAgendaEvent(event.kind, event.starts_at, event.ends_at, event.status)
            for event in process_events
        ],
        DashboardFilters(start_at, end_at, timezone_name, source_key),
    )
    return DashboardResponse.model_validate(result)
