"""Persistence and execution primitives for unified local scheduled searches."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship, sessionmaker

from job_finder.aggregated_search import JobProvider, JobSearchParams, SearchAggregator
from job_finder.database import Base
from job_finder.source_adapters import CancellationToken
from job_finder.source_dedup import DedupeKind, DedupeResult, ingest_candidate

ScheduledRunStatus = Literal["pending", "running", "completed", "partial", "failed", "cancelled"]
ScheduledDedupeKind = Literal["created", "exact", "approximate"]


class ScheduledSearchRecord(Base):
    """One persisted query that can be executed while the local app is open."""

    __tablename__ = "scheduled_searches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    query: Mapped[str] = mapped_column(String(120), nullable=False)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    work_model: Mapped[str] = mapped_column(String(16), nullable=False, default="all")
    limit: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    frequency_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=1440)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    profile_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("profile_versions.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    runs: Mapped[list[ScheduledSearchRunRecord]] = relationship(
        back_populates="schedule", cascade="all, delete-orphan"
    )


class ScheduledSearchRunRecord(Base):
    """One auditable execution of a scheduled unified search."""

    __tablename__ = "scheduled_search_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scheduled_search_id: Mapped[int] = mapped_column(
        ForeignKey("scheduled_searches.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    query: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    candidates_seen: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    jobs_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    exact_duplicates: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    approximate_duplicates: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_runs: Mapped[list[dict[str, object]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    schedule: Mapped[ScheduledSearchRecord] = relationship(back_populates="runs")
    jobs: Mapped[list[ScheduledSearchJobRecord]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class ScheduledSearchJobRecord(Base):
    """Link between an execution and the local job/dedupe outcome it produced."""

    __tablename__ = "scheduled_search_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("scheduled_search_runs.id"), nullable=False)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id"), nullable=True)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    candidate: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    run: Mapped[ScheduledSearchRunRecord] = relationship(back_populates="jobs")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def schedule_next_run(schedule: ScheduledSearchRecord, now: datetime | None = None) -> None:
    schedule.next_run_at = (now or utc_now()) + timedelta(minutes=schedule.frequency_minutes)


def due_scheduled_searches(
    session: Session, now: datetime | None = None
) -> list[ScheduledSearchRecord]:
    current = now or utc_now()
    return list(
        session.scalars(
            select(ScheduledSearchRecord)
            .where(
                ScheduledSearchRecord.enabled.is_(True),
                (ScheduledSearchRecord.next_run_at.is_(None))
                | (ScheduledSearchRecord.next_run_at <= current),
            )
            .order_by(ScheduledSearchRecord.id)
        )
    )


def create_scheduled_run(
    session: Session, schedule: ScheduledSearchRecord, now: datetime | None = None
) -> ScheduledSearchRunRecord:
    current = now or utc_now()
    run = ScheduledSearchRunRecord(
        schedule=schedule,
        status="pending",
        query={
            "query": schedule.query,
            "location": schedule.location,
            "work_model": schedule.work_model,
            "limit": schedule.limit,
        },
        requested_at=current,
    )
    session.add(run)
    session.flush()
    schedule.last_run_at = current
    schedule_next_run(schedule, current)
    return run


def _dedupe_job_id(result: DedupeResult) -> int | None:
    if result.job is not None:
        return result.job.id
    return result.suggestion.existing_job_id if result.suggestion is not None else None


async def execute_scheduled_search(
    session_factory: sessionmaker[Session],
    run_id: int,
    providers: list[JobProvider],
    *,
    minimum_results: int = 1,
) -> ScheduledSearchRunRecord:
    """Execute one scheduled query and commit each valid candidate independently."""

    from time import monotonic

    started_clock = monotonic()
    with session_factory() as session:
        run = session.get(ScheduledSearchRunRecord, run_id)
        if run is None:
            raise ValueError("Execução agendada não encontrada.")
        schedule = session.get(ScheduledSearchRecord, run.scheduled_search_id)
        if schedule is None:
            raise ValueError("Agenda não encontrada.")
        run.status = "running"
        run.started_at = utc_now()
        session.commit()

    params = JobSearchParams.model_validate(run.query)
    aggregator = SearchAggregator(providers, minimum_results=minimum_results)
    result = await aggregator.search(params, cancellation=CancellationToken())
    with session_factory() as session:
        run = session.get(ScheduledSearchRunRecord, run_id)
        if run is None:
            raise ValueError("Execução agendada não encontrada.")
        run.provider_runs = [dict(provider_run.__dict__) for provider_run in result.provider_runs]
        run.candidates_seen = len(result.candidates)
        persistence_errors: list[str] = []
        for candidate in result.candidates:
            try:
                dedupe_result = ingest_candidate(session, candidate)
                outcome = dedupe_result.kind
                job_id = _dedupe_job_id(dedupe_result)
                session.add(
                    ScheduledSearchJobRecord(
                        run_id=run.id,
                        job_id=job_id,
                        provider=candidate.source_key,
                        outcome=outcome,
                        candidate=candidate.as_payload(),
                    )
                )
                if dedupe_result.kind == DedupeKind.CREATED:
                    run.jobs_created += 1
                elif dedupe_result.kind == DedupeKind.EXACT:
                    run.exact_duplicates += 1
                else:
                    run.approximate_duplicates += 1
                session.commit()
            except Exception as error:  # keep previously persisted candidates intact
                session.rollback()
                persistence_errors.append(type(error).__name__)
        if persistence_errors:
            run.status = "partial" if run.jobs_created or run.exact_duplicates else "failed"
            run.error_message = (
                f"Falha ao persistir {len(persistence_errors)} vaga(s): "
                + ", ".join(persistence_errors)
            )
        elif result.outcome == "partial" or result.partial:
            run.status = "partial"
            run.error_message = "; ".join(result.warnings) if result.warnings else None
        elif result.outcome == "failed":
            run.status = "failed"
            run.error_message = "; ".join(result.warnings) or result.message
        else:
            run.status = "completed"
            run.error_message = None
        run.finished_at = utc_now()
        run.duration_ms = max(0, round((monotonic() - started_clock) * 1000))
        session.commit()
    with session_factory() as final_session:
        final = final_session.get(ScheduledSearchRunRecord, run_id)
        if final is None:
            raise ValueError("Execução agendada não finalizada.")
        return final
