"""Normalized job persistence, source origins and immutable content history."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
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
from sqlalchemy.orm import Mapped, Mapper, Session, mapped_column, relationship

from job_finder.database import Base

NonEmptyJobText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=240),
]
CanonicalUrl = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=2048),
]
SourceName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=80),
]
ExternalIdentifier = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]


class JobDraft(BaseModel):
    """Normalized fields shared by every origin of one logical job."""

    model_config = ConfigDict(extra="forbid")

    canonical_url: CanonicalUrl | None = None
    title: NonEmptyJobText
    company: NonEmptyJobText
    location: NonEmptyJobText | None = None
    published_at: datetime | None = None
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "JobDraft":
        """Keep normalized validity dates timezone-aware and ordered."""

        for field_name in ("published_at", "expires_at"):
            timestamp = getattr(self, field_name)
            if timestamp is not None and timestamp.tzinfo is None:
                raise ValueError(f"{field_name} must include timezone information")
        if (
            self.published_at is not None
            and self.expires_at is not None
            and self.expires_at < self.published_at
        ):
            raise ValueError("expires_at must be greater than or equal to published_at")
        return self


class JobOriginDraft(BaseModel):
    """Identity and traceability data supplied by one job source."""

    model_config = ConfigDict(extra="forbid")

    source: SourceName
    external_id: ExternalIdentifier | None = None
    url: CanonicalUrl | None = None


class JobContentDraft(BaseModel):
    """One captured raw representation and the period where it is valid."""

    model_config = ConfigDict(extra="forbid")

    raw_content: str = Field(min_length=1)
    content_type: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=120),
    ] = "text/plain"
    captured_at: datetime
    valid_from: datetime
    valid_until: datetime | None = None

    @model_validator(mode="after")
    def validate_validity_window(self) -> "JobContentDraft":
        """Require timezone-aware timestamps and a non-inverted validity interval."""

        for field_name in ("captured_at", "valid_from", "valid_until"):
            timestamp = getattr(self, field_name)
            if timestamp is not None and timestamp.tzinfo is None:
                raise ValueError(f"{field_name} must include timezone information")

        if self.valid_until is not None and self.valid_until < self.valid_from:
            raise ValueError("valid_until must be greater than or equal to valid_from")
        return self


class Job(Base):
    """One normalized logical job that can be represented by many origins."""

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_url: Mapped[str | None] = mapped_column(String(2048), unique=True, nullable=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    company: Mapped[str] = mapped_column(String(240), nullable=False)
    location: Mapped[str | None] = mapped_column(String(240), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
    origins: Mapped[list["JobOrigin"]] = relationship(
        back_populates="job",
        order_by="JobOrigin.id",
        cascade="all, delete-orphan",
    )


class JobOrigin(Base):
    """One auditable source representation attached to a normalized job."""

    __tablename__ = "job_origins"
    __table_args__ = (UniqueConstraint("job_id", "source", "external_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), nullable=False)
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    job: Mapped[Job] = relationship(back_populates="origins")
    content_versions: Mapped[list["JobContentVersion"]] = relationship(
        back_populates="origin",
        order_by="JobContentVersion.version_number",
        cascade="all, delete-orphan",
    )


class JobContentVersion(Base):
    """Immutable raw content captured from one origin over a validity interval."""

    __tablename__ = "job_content_versions"
    __table_args__ = (UniqueConstraint("origin_id", "version_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    origin_id: Mapped[int] = mapped_column(ForeignKey("job_origins.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    origin: Mapped[JobOrigin] = relationship(back_populates="content_versions")


class ImmutableJobContentVersionError(RuntimeError):
    """Raised when a captured raw content version would lose its audit trail."""


@event.listens_for(JobContentVersion, "before_update")
def prevent_job_content_version_update(
    _mapper: Mapper[JobContentVersion],
    _connection: Connection,
    _target: JobContentVersion,
) -> None:
    """Keep every captured representation immutable after persistence."""

    raise ImmutableJobContentVersionError(
        "Job content versions are immutable. Capture a new version instead."
    )


@event.listens_for(JobContentVersion, "before_delete")
def prevent_job_content_version_delete(
    _mapper: Mapper[JobContentVersion],
    _connection: Connection,
    _target: JobContentVersion,
) -> None:
    """Preserve source evidence instead of allowing historical content to disappear."""

    raise ImmutableJobContentVersionError("Job content versions cannot be deleted.")


def create_job(session: Session, draft: JobDraft) -> Job:
    """Persist one normalized job without discarding source-specific evidence."""

    job = Job(
        canonical_url=draft.canonical_url,
        title=draft.title,
        company=draft.company,
        location=draft.location,
        published_at=draft.published_at,
        expires_at=draft.expires_at,
    )
    session.add(job)
    session.flush()
    return job


def get_job(session: Session, job_id: int) -> Job | None:
    """Return one normalized job by its local identifier."""

    return session.get(Job, job_id)


def add_job_origin(session: Session, job_id: int, draft: JobOriginDraft) -> JobOrigin:
    """Attach a source identity to an existing normalized job."""

    job = session.get(Job, job_id)
    if job is None:
        raise ValueError(f"Job {job_id} does not exist.")

    origin = JobOrigin(
        job=job,
        source=draft.source,
        external_id=draft.external_id,
        url=draft.url,
    )
    session.add(origin)
    session.flush()
    return origin


def get_job_origins(session: Session, job_id: int) -> list[JobOrigin]:
    """Return all source origins in stable insertion order."""

    statement = select(JobOrigin).where(JobOrigin.job_id == job_id).order_by(JobOrigin.id)
    return list(session.scalars(statement))


def add_job_content_version(
    session: Session,
    origin_id: int,
    draft: JobContentDraft,
) -> JobContentVersion:
    """Append an immutable raw-content snapshot to an existing source origin."""

    origin = session.get(JobOrigin, origin_id)
    if origin is None:
        raise ValueError(f"Job origin {origin_id} does not exist.")

    current_version = session.scalar(
        select(func.max(JobContentVersion.version_number)).where(
            JobContentVersion.origin_id == origin_id
        )
    )
    version = JobContentVersion(
        origin=origin,
        version_number=(current_version or 0) + 1,
        raw_content=draft.raw_content,
        content_type=draft.content_type,
        captured_at=draft.captured_at,
        valid_from=draft.valid_from,
        valid_until=draft.valid_until,
    )
    session.add(version)
    session.flush()
    return version


def get_job_content_versions(session: Session, origin_id: int) -> list[JobContentVersion]:
    """Return every captured content version for one origin."""

    statement = (
        select(JobContentVersion)
        .where(JobContentVersion.origin_id == origin_id)
        .order_by(JobContentVersion.version_number)
    )
    return list(session.scalars(statement))
