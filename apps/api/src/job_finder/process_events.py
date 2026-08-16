"""Process events linked to an application: interviews, challenges and deadlines."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from job_finder.applications import Application
from job_finder.database import Base

ProcessEventKind = Literal["interview", "challenge", "deadline"]
ProcessEventStatus = Literal["scheduled", "completed", "cancelled"]


class EventTimeError(ValueError):
    """Raised when an event has invalid or timezone-naive timestamps."""


class EventConflictError(ValueError):
    """Raised when two active events overlap for the same application."""


@dataclass(frozen=True)
class ProcessEventDraft:
    """Validated input used to create one process event."""

    kind: ProcessEventKind
    title: str
    starts_at: datetime
    ends_at: datetime | None = None
    participants: list[str] = field(default_factory=list)
    link: str | None = None
    notes: str | None = None
    timezone_name: str | None = None


class ProcessEvent(Base):
    """A scheduled process event that remains linked to its application."""

    __tablename__ = "process_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    timezone_name: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    participants: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    link: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="scheduled")


def create_process_event(
    session: Session,
    application_id: int,
    draft: ProcessEventDraft,
) -> ProcessEvent:
    """Validate and persist an event, rejecting overlapping active events."""

    if session.get(Application, application_id) is None:
        raise ValueError(f"Application {application_id} does not exist.")

    starts_at = _to_utc_naive(draft.starts_at)
    ends_at = _to_utc_naive(draft.ends_at) if draft.ends_at is not None else None
    if ends_at is not None and ends_at < starts_at:
        raise EventTimeError("Event end must be after its start.")

    existing_events = session.scalars(
        select(ProcessEvent)
        .where(ProcessEvent.application_id == application_id)
        .where(ProcessEvent.status != "cancelled")
    ).all()
    if any(_events_overlap(event, starts_at, ends_at) for event in existing_events):
        raise EventConflictError("Event conflict: process events cannot overlap.")

    event = ProcessEvent(
        application_id=application_id,
        kind=draft.kind,
        title=draft.title.strip(),
        starts_at=starts_at,
        ends_at=ends_at,
        timezone_name=draft.timezone_name or _timezone_name(draft.starts_at),
        participants=[item.strip() for item in draft.participants if item.strip()],
        link=draft.link,
        notes=draft.notes,
        status="scheduled",
    )
    session.add(event)
    session.flush()
    return event


def get_process_events(session: Session, application_id: int) -> list[ProcessEvent]:
    """Return process events in chronological order."""

    statement = (
        select(ProcessEvent)
        .where(ProcessEvent.application_id == application_id)
        .order_by(ProcessEvent.starts_at, ProcessEvent.id)
    )
    return list(session.scalars(statement))


def is_event_overdue(event: ProcessEvent, now: datetime) -> bool:
    """Return whether a scheduled event has passed its end (or start) time."""

    cutoff = event.ends_at or event.starts_at
    return event.status == "scheduled" and cutoff <= _to_utc_naive(now)


def _to_utc_naive(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise EventTimeError("Event timestamps must include a timezone.")
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _timezone_name(value: datetime) -> str:
    tzinfo = value.tzinfo
    name = tzinfo.tzname(value) if tzinfo is not None else None
    return name or "UTC"


def _events_overlap(
    existing: ProcessEvent,
    starts_at: datetime,
    ends_at: datetime | None,
) -> bool:
    existing_end = existing.ends_at or existing.starts_at
    incoming_end = ends_at or starts_at
    if existing.ends_at is None and ends_at is None:
        return existing.starts_at == starts_at
    return existing.starts_at < incoming_end and starts_at < existing_end
