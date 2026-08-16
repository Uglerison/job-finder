"""Application aggregate with an immutable event history."""

from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
    func,
    select,
)
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Mapped, Mapper, Session, mapped_column

from job_finder.database import Base

ApplicationStatus = Literal[
    "found",
    "pending",
    "applied",
    "interview",
    "offer",
    "hired",
    "rejected",
    "withdrawn",
    "expired",
]
ApplicationEventKind = Literal["initial", "transition", "correction"]
ClosingReason = Literal["not_fit", "no_response", "role_closed", "candidate_withdrew", "other"]


class Application(Base):
    """One application aggregate, unique for each normalized job."""

    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), unique=True, nullable=False)
    current_status: Mapped[str] = mapped_column(String(32), nullable=False, default="found")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    closing_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ApplicationEvent(Base):
    """Immutable fact describing one application state change."""

    __tablename__ = "application_events"
    __table_args__ = (UniqueConstraint("application_id", "sequence_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    closure_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ImmutableApplicationEventError(RuntimeError):
    """Raised when an audit event would be changed or removed."""


@event.listens_for(ApplicationEvent, "before_update")
def prevent_application_event_update(
    _mapper: Mapper[ApplicationEvent], _connection: Connection, _target: ApplicationEvent
) -> None:
    raise ImmutableApplicationEventError("Application events are immutable.")


@event.listens_for(ApplicationEvent, "before_delete")
def prevent_application_event_delete(
    _mapper: Mapper[ApplicationEvent], _connection: Connection, _target: ApplicationEvent
) -> None:
    raise ImmutableApplicationEventError("Application events cannot be deleted.")


def create_application(session: Session, job_id: int) -> Application:
    """Create one application with an initial `found` event."""

    from job_finder.jobs import Job

    if session.get(Job, job_id) is None:
        raise ValueError(f"Job {job_id} does not exist.")
    existing = session.scalar(select(Application).where(Application.job_id == job_id))
    if existing is not None:
        raise ValueError("Application already exists for this job.")

    application = Application(job_id=job_id, current_status="found")
    session.add(application)
    session.flush()
    session.add(
        ApplicationEvent(
            application_id=application.id,
            sequence_number=1,
            kind="initial",
            from_status=None,
            to_status="found",
        )
    )
    session.flush()
    return application


def get_application(session: Session, application_id: int) -> Application | None:
    return session.get(Application, application_id)


def get_application_for_job(session: Session, job_id: int) -> Application | None:
    return session.scalar(select(Application).where(Application.job_id == job_id))


def mark_application_applied(session: Session, job_id: int) -> Application:
    """Atomically create or advance a job application to ``applied``.

    The operation is intentionally idempotent when the application is already
    marked as applied. Once an application has advanced to a later phase, the
    shortcut cannot move it backwards; callers must use the explicit
    transition endpoint with its correction/audit semantics instead.
    """

    application = get_application_for_job(session, job_id)
    if application is None:
        application = create_application(session, job_id)

    if application.current_status == "applied":
        return application
    if application.current_status not in {"found", "pending"}:
        raise ValueError(f"Application already advanced to {application.current_status}.")

    # Imported at call time to keep the domain modules free of an import cycle.
    from job_finder.pipeline import transition_application

    transition_application(session, application, "applied")
    return application


def get_application_events(session: Session, application_id: int) -> list[ApplicationEvent]:
    statement = (
        select(ApplicationEvent)
        .where(ApplicationEvent.application_id == application_id)
        .order_by(ApplicationEvent.sequence_number)
    )
    return list(session.scalars(statement))


def append_application_event(
    session: Session,
    application: Application,
    *,
    kind: ApplicationEventKind,
    to_status: ApplicationStatus,
    note: str | None = None,
    closure_reason: ClosingReason | None = None,
) -> ApplicationEvent:
    """Append a state fact and update the aggregate's current status transactionally."""

    current_sequence = session.scalar(
        select(func.max(ApplicationEvent.sequence_number)).where(
            ApplicationEvent.application_id == application.id
        )
    )
    event_record = ApplicationEvent(
        application_id=application.id,
        sequence_number=(current_sequence or 0) + 1,
        kind=kind,
        from_status=application.current_status,
        to_status=to_status,
        note=note,
        closure_reason=closure_reason,
    )
    application.current_status = to_status
    application.closing_reason = closure_reason
    application.closed_at = datetime.now(timezone.utc) if closure_reason else None
    session.add(event_record)
    session.flush()
    return event_record
