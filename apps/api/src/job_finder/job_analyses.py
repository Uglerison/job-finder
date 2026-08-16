"""Append-only persistence for provenance-rich AI job analyses."""

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    event,
    func,
    select,
)
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Mapped, Mapper, Session, mapped_column

from job_finder.database import Base


@dataclass(frozen=True)
class JobAnalysisVersionDraft:
    """One fully validated result and the immutable inputs that produced it."""

    profile_version_id: int
    job_id: int
    job_content_version_id: int
    model: str
    prompt_version: str
    analysis: dict[str, object]
    fit: dict[str, object]
    explanation: dict[str, object]
    usage: dict[str, object] = field(default_factory=dict)


class JobAnalysisVersion(Base):
    """A historical analysis snapshot that is never overwritten by re-analysis."""

    __tablename__ = "job_analysis_versions"
    __table_args__ = (UniqueConstraint("job_id", "version_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), nullable=False)
    job_content_version_id: Mapped[int] = mapped_column(
        ForeignKey("job_content_versions.id"),
        nullable=False,
    )
    profile_version_id: Mapped[int] = mapped_column(
        ForeignKey("profile_versions.id"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(120), nullable=False)
    analysis: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    fit: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    explanation: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    usage: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ImmutableJobAnalysisVersionError(RuntimeError):
    """Raised when a retained analysis would lose its historical integrity."""


@event.listens_for(JobAnalysisVersion, "before_update")
def prevent_job_analysis_version_update(
    _mapper: Mapper[JobAnalysisVersion],
    _connection: Connection,
    _target: JobAnalysisVersion,
) -> None:
    """Preserve the original profile, prompt, model and output of every run."""

    raise ImmutableJobAnalysisVersionError(
        "Job analysis versions are immutable. Create a new analysis version."
    )


@event.listens_for(JobAnalysisVersion, "before_delete")
def prevent_job_analysis_version_delete(
    _mapper: Mapper[JobAnalysisVersion],
    _connection: Connection,
    _target: JobAnalysisVersion,
) -> None:
    """Keep audit history even when another analysis becomes the current one."""

    raise ImmutableJobAnalysisVersionError("Job analysis versions cannot be deleted.")


def create_job_analysis_version(
    session: Session,
    draft: JobAnalysisVersionDraft,
) -> JobAnalysisVersion:
    """Append a new per-job version without changing prior retained analyses."""

    current_version = session.scalar(
        select(func.max(JobAnalysisVersion.version_number)).where(
            JobAnalysisVersion.job_id == draft.job_id
        )
    )
    record = JobAnalysisVersion(
        profile_version_id=draft.profile_version_id,
        job_id=draft.job_id,
        job_content_version_id=draft.job_content_version_id,
        version_number=(current_version or 0) + 1,
        model=draft.model,
        prompt_version=draft.prompt_version,
        analysis=draft.analysis,
        fit=draft.fit,
        explanation=draft.explanation,
        usage=draft.usage or {},
    )
    session.add(record)
    session.flush()
    return record


def get_job_analysis_versions(session: Session, job_id: int) -> list[JobAnalysisVersion]:
    """Return each historical analysis in the order it was generated."""

    statement = (
        select(JobAnalysisVersion)
        .where(JobAnalysisVersion.job_id == job_id)
        .order_by(JobAnalysisVersion.version_number)
    )
    return list(session.scalars(statement))
