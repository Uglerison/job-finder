"""Persistent configuration and audit records for web job sources."""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    select,
)
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from job_finder.database import Base
from job_finder.job_import import validate_public_url

SourceKey = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=2,
        max_length=64,
        pattern=r"^[a-z0-9][a-z0-9_-]*$",
    ),
]
SourceRunStatus = Literal["pending", "running", "completed", "partial", "failed", "cancelled"]
DuplicateStatus = Literal["pending", "confirmed", "dismissed"]


class SourceConfigData(BaseModel):
    """User-editable source settings; no credential value is accepted here."""

    model_config = ConfigDict(extra="forbid")

    source_key: SourceKey
    display_name: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=120),
    ]
    endpoint: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=2048),
    ]
    terms_url: Annotated[
        str,
        StringConstraints(strip_whitespace=True, max_length=2048),
    ] | None = None
    data_format: Literal["json"] = "json"
    enabled: bool = True
    schedule_enabled: bool = False
    frequency_minutes: int = Field(default=1440, ge=15, le=10080)
    daily_limit: int = Field(default=50, ge=1, le=1000)
    per_run_limit: int = Field(default=50, ge=1, le=200)
    timeout_seconds: int = Field(default=15, ge=1, le=60)

    @field_validator("endpoint", "terms_url")
    @classmethod
    def public_http_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("A fonte deve usar uma URL HTTP(S) pública.")
        if parsed.username or parsed.password:
            raise ValueError("A URL da fonte não pode conter credenciais.")
        try:
            return validate_public_url(value)
        except ValueError as error:
            raise ValueError(str(error)) from error


class SourceConfigResponse(SourceConfigData):
    """Public source state returned without secret references."""

    id: int
    last_run_at: datetime | None
    next_run_at: datetime | None
    backoff_until: datetime | None
    consecutive_failures: int
    last_error: str | None


class SourceConfigRecord(Base):
    """Persisted source configuration and operational state."""

    __tablename__ = "source_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(2048), nullable=False)
    terms_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    data_format: Mapped[str] = mapped_column(String(32), nullable=False, default="json")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    schedule_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    frequency_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=1440)
    daily_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    per_run_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    secret_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    backoff_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    runs: Mapped[list["SearchRunRecord"]] = relationship(back_populates="source")


class SearchRunRecord(Base):
    """One persisted source execution and its counters."""

    __tablename__ = "search_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_config_id: Mapped[int] = mapped_column(ForeignKey("source_configs.id"), nullable=False)
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
    cancellation_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    current_cursor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[SourceConfigRecord] = relationship(back_populates="runs")


class DuplicateSuggestionRecord(Base):
    """Approximate duplicate pending an explicit user decision."""

    __tablename__ = "duplicate_suggestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    existing_job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), nullable=False)
    source_key: Mapped[str] = mapped_column(String(64), nullable=False)
    candidate: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    similarity: Mapped[float] = mapped_column(Float, nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


DEFAULT_SOURCE_CONFIGS: tuple[SourceConfigData, ...] = (
    SourceConfigData(
        source_key="remoteok",
        display_name="Remote OK",
        endpoint="https://remoteok.com/api",
        terms_url="https://remoteok.com/terms",
        per_run_limit=50,
    ),
    SourceConfigData(
        source_key="arbeitnow",
        display_name="Arbeitnow",
        endpoint="https://www.arbeitnow.com/api/job-board-api",
        terms_url="https://www.arbeitnow.com/terms",
        per_run_limit=50,
    ),
    SourceConfigData(
        source_key="jobicy",
        display_name="Jobicy",
        endpoint="https://jobicy.com/api/v2/remote-jobs?count=50",
        terms_url="https://jobicy.com/terms",
        per_run_limit=50,
    ),
)


def utc_now() -> datetime:
    """Return an aware UTC timestamp for domain logic and API responses."""

    return datetime.now(timezone.utc)


def ensure_default_sources(session: Session) -> list[SourceConfigRecord]:
    """Seed the three approved public sources once, preserving user edits."""

    existing = {record.source_key: record for record in session.scalars(select(SourceConfigRecord))}
    records: list[SourceConfigRecord] = []
    for default in DEFAULT_SOURCE_CONFIGS:
        record = existing.get(default.source_key)
        if record is None:
            record = SourceConfigRecord(**default.model_dump())
            session.add(record)
            session.flush()
        records.append(record)
    return records


def source_data(record: SourceConfigRecord) -> SourceConfigData:
    """Convert a persisted record to a validated public configuration."""

    return SourceConfigData.model_validate(
        {
            "source_key": record.source_key,
            "display_name": record.display_name,
            "endpoint": record.endpoint,
            "terms_url": record.terms_url,
            "data_format": record.data_format,
            "enabled": record.enabled,
            "schedule_enabled": record.schedule_enabled,
            "frequency_minutes": record.frequency_minutes,
            "daily_limit": record.daily_limit,
            "per_run_limit": record.per_run_limit,
            "timeout_seconds": record.timeout_seconds,
        },
    )


def source_response(record: SourceConfigRecord) -> SourceConfigResponse:
    """Build the API response while omitting secret_ref."""

    return SourceConfigResponse(
        **source_data(record).model_dump(),
        id=record.id,
        last_run_at=record.last_run_at,
        next_run_at=record.next_run_at,
        backoff_until=record.backoff_until,
        consecutive_failures=record.consecutive_failures,
        last_error=record.last_error,
    )


def create_search_run(
    session: Session,
    source: SourceConfigRecord,
    query: dict[str, object],
) -> SearchRunRecord:
    """Create a pending run with an immutable copy of its search parameters."""

    run = SearchRunRecord(
        source=source,
        status="pending",
        query=dict(query),
        requested_at=utc_now(),
    )
    session.add(run)
    session.flush()
    return run


def schedule_next_run(source: SourceConfigRecord, now: datetime | None = None) -> None:
    """Persist the next execution window in the source's configured timezone-free UTC."""

    source.next_run_at = (now or utc_now()) + timedelta(minutes=source.frequency_minutes)


def due_sources(session: Session, now: datetime | None = None) -> list[SourceConfigRecord]:
    """Return enabled scheduled sources whose next run is due and not backed off."""

    current = now or utc_now()
    statement = select(SourceConfigRecord).where(
        SourceConfigRecord.enabled.is_(True),
        SourceConfigRecord.schedule_enabled.is_(True),
    )
    records = list(session.scalars(statement))
    return [
        record
        for record in records
        if (record.next_run_at is None or record.next_run_at <= current)
        and (record.backoff_until is None or record.backoff_until <= current)
    ]
