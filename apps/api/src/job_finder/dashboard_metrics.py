"""Pure, auditable dashboard aggregations used by the local API and tests."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

APPLIED_STATUSES = {"applied", "interview", "offer", "hired", "rejected", "withdrawn", "expired"}
INTERVIEW_STATUSES = {"interview", "offer", "hired"}
OFFER_STATUSES = {"offer", "hired"}


@dataclass(frozen=True)
class MetricApplicationEvent:
    to_status: str
    occurred_at: datetime


@dataclass(frozen=True)
class MetricJob:
    id: int
    created_at: datetime
    origins: tuple[str, ...] = ()
    deleted_at: datetime | None = None


@dataclass(frozen=True)
class MetricApplication:
    job_id: int
    created_at: datetime
    current_status: str
    events: tuple[MetricApplicationEvent, ...] = ()


@dataclass(frozen=True)
class MetricSearchRun:
    source_key: str
    requested_at: datetime
    status: str
    jobs_created: int = 0
    error_message: str | None = None


@dataclass(frozen=True)
class MetricAgendaEvent:
    kind: str
    starts_at: datetime
    ends_at: datetime | None
    status: str


@dataclass(frozen=True)
class DashboardFilters:
    from_at: datetime
    to_at: datetime
    timezone_name: str = "America/Sao_Paulo"
    source_key: str | None = None


def build_dashboard(
    jobs: list[MetricJob],
    applications: list[MetricApplication],
    runs: list[MetricSearchRun],
    agenda_events: list[MetricAgendaEvent],
    filters: DashboardFilters,
) -> dict[str, object]:
    """Build all E6 cards from distinct local entities, excluding deleted jobs."""

    timezone_info = _timezone(filters.timezone_name)
    active_jobs = [
        job
        for job in jobs
        if job.deleted_at is None
        and _in_period(job.created_at, filters)
        and _source_matches(job, filters.source_key)
    ]
    job_ids = {job.id for job in active_jobs}
    relevant_applications = [
        application
        for application in applications
        if application.job_id in job_ids and _in_period(application.created_at, filters)
    ]
    cards = _cards(active_jobs, relevant_applications)
    funnel = _funnel(len(active_jobs), relevant_applications)
    series = _series(active_jobs, relevant_applications, filters, timezone_info)
    sources = _source_performance(
        active_jobs,
        relevant_applications,
        runs,
        filters,
    )
    now = datetime.now(timezone.utc)
    upcoming = [
        event
        for event in agenda_events
        if event.status == "scheduled" and _as_utc(event.ends_at or event.starts_at) >= now
    ]
    overdue = [
        event
        for event in agenda_events
        if event.status == "scheduled" and _as_utc(event.ends_at or event.starts_at) < now
    ]
    return {
        "period": {
            "from_": filters.from_at.isoformat(),
            "to": filters.to_at.isoformat(),
            "timezone": filters.timezone_name,
            "source_key": filters.source_key,
        },
        "cards": cards,
        "funnel": funnel,
        "series": series,
        "sources": sources,
        "agenda": {
            "upcoming": len(upcoming),
            "overdue": len(overdue),
        },
    }


def _cards(
    jobs: list[MetricJob],
    applications: list[MetricApplication],
) -> dict[str, int]:
    statuses = [application.current_status for application in applications]
    return {
        "jobs_found": len({job.id for job in jobs}),
        "applications": len(applications),
        "interviews": sum(status in INTERVIEW_STATUSES for status in statuses),
        "offers": sum(status in OFFER_STATUSES for status in statuses),
        "hired": sum(status == "hired" for status in statuses),
        "rejected": sum(status == "rejected" for status in statuses),
        "active_pipeline": sum(
            status not in {"rejected", "withdrawn", "expired", "hired"} for status in statuses
        ),
    }


def _funnel(
    found_count: int,
    applications: list[MetricApplication],
) -> list[dict[str, object]]:
    statuses = [application.current_status for application in applications]
    stages = [
        ("found", "Encontradas", found_count, found_count),
        (
            "applied",
            "Aplicadas",
            sum(status in APPLIED_STATUSES for status in statuses),
            found_count,
        ),
        (
            "interview",
            "Entrevistas",
            sum(status in INTERVIEW_STATUSES for status in statuses),
            sum(status in APPLIED_STATUSES for status in statuses),
        ),
        (
            "offer",
            "Ofertas",
            sum(status in OFFER_STATUSES for status in statuses),
            sum(status in INTERVIEW_STATUSES for status in statuses),
        ),
        (
            "hired",
            "Contratadas",
            sum(status == "hired" for status in statuses),
            sum(status in OFFER_STATUSES for status in statuses),
        ),
    ]
    return [
        {
            "key": key,
            "label": label,
            "count": count,
            "denominator": denominator,
            "conversion_percent": round(count / denominator * 100, 1) if denominator else None,
        }
        for key, label, count, denominator in stages
    ]


def _series(
    jobs: list[MetricJob],
    applications: list[MetricApplication],
    filters: DashboardFilters,
    timezone_info: tzinfo,
) -> list[dict[str, object]]:
    start_local = _as_utc(filters.from_at).astimezone(timezone_info)
    end_local = _as_utc(filters.to_at).astimezone(timezone_info)
    cursor = (start_local - timedelta(days=start_local.weekday())).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    points: list[dict[str, object]] = []
    while cursor < end_local:
        next_cursor = cursor + timedelta(days=7)
        jobs_count = sum(
            cursor <= _as_utc(job.created_at).astimezone(timezone_info) < next_cursor
            for job in jobs
        )
        apps_count = sum(
            cursor <= _as_utc(application.created_at).astimezone(timezone_info) < next_cursor
            for application in applications
        )
        interviews_count = sum(
            any(
                event.to_status in INTERVIEW_STATUSES
                and cursor <= _as_utc(event.occurred_at).astimezone(timezone_info) < next_cursor
                for event in application.events
            )
            for application in applications
        )
        points.append(
            {
                "period_start": cursor.date().isoformat(),
                "jobs": jobs_count,
                "applications": apps_count,
                "interviews": interviews_count,
            }
        )
        cursor = next_cursor
    return points


def _source_performance(
    jobs: list[MetricJob],
    applications: list[MetricApplication],
    runs: list[MetricSearchRun],
    filters: DashboardFilters,
) -> list[dict[str, object]]:
    by_job = {application.job_id: application for application in applications}
    grouped: dict[str, dict[str, int]] = defaultdict(
        lambda: {"jobs": 0, "applications": 0, "interviews": 0, "errors": 0}
    )
    for job in jobs:
        source = job.origins[0] if job.origins else "manual"
        grouped[source]["jobs"] += 1
        application = by_job.get(job.id)
        if application:
            grouped[source]["applications"] += 1
            grouped[source]["interviews"] += application.current_status in INTERVIEW_STATUSES
    for run in runs:
        if not _in_period(run.requested_at, filters):
            continue
        if filters.source_key and run.source_key != filters.source_key:
            continue
        grouped[run.source_key]["errors"] += run.status in {"failed", "partial"}
    return [
        {
            "source_key": source,
            **values,
            "application_rate_percent": round(values["applications"] / values["jobs"] * 100, 1)
            if values["jobs"]
            else None,
        }
        for source, values in sorted(grouped.items())
    ]


def _source_matches(job: MetricJob, source_key: str | None) -> bool:
    return source_key is None or source_key in job.origins


def _in_period(value: datetime, filters: DashboardFilters) -> bool:
    instant = _as_utc(value)
    return _as_utc(filters.from_at) <= instant < _as_utc(filters.to_at)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _timezone(name: str) -> tzinfo:
    """Use bundled IANA data when present, with a deterministic Brazil fallback."""

    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        if name == "America/Sao_Paulo":
            return timezone(timedelta(hours=-3), name=name)
        if name.upper() in {"UTC", "ETC/UTC"}:
            return timezone.utc
        raise ValueError(f"Fuso horário inválido: {name}") from None
