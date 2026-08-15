"""Editable notes and reusable tags attached to normalized jobs."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from job_finder.database import Base


class JobNote(Base):
    """A user-authored note that can be edited without changing the job."""

    __tablename__ = "job_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class JobTag(Base):
    """A normalized tag shared by any number of jobs."""

    __tablename__ = "job_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)


class JobTagLink(Base):
    """Many-to-many link between one job and one normalized tag."""

    __tablename__ = "job_tag_links"
    __table_args__ = (UniqueConstraint("job_id", "tag_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), nullable=False)
    tag_id: Mapped[int] = mapped_column(ForeignKey("job_tags.id"), nullable=False)


def get_job_notes(session: Session, job_id: int) -> list[JobNote]:
    """Return notes newest-first for a job."""

    statement = (
        select(JobNote)
        .where(JobNote.job_id == job_id)
        .order_by(JobNote.created_at.desc(), JobNote.id.desc())
    )
    return list(session.scalars(statement))


def create_job_note(session: Session, job_id: int, body: str) -> JobNote:
    """Create a note after confirming that the target job exists."""

    _require_job(session, job_id)
    note = JobNote(job_id=job_id, body=body)
    session.add(note)
    session.flush()
    return note


def get_job_note(session: Session, job_id: int, note_id: int) -> JobNote | None:
    """Return one note only when it belongs to the requested job."""

    statement = select(JobNote).where(JobNote.id == note_id, JobNote.job_id == job_id)
    return session.scalar(statement)


def update_job_note(session: Session, note: JobNote, body: str) -> JobNote:
    """Replace note text while retaining its creation timestamp."""

    note.body = body
    session.flush()
    return note


def delete_job_note(session: Session, note: JobNote) -> None:
    """Remove one user note without touching the job record."""

    session.delete(note)
    session.flush()


def normalize_tag_name(value: str) -> str:
    """Keep tags compact and case-insensitive for filtering."""

    normalized = " ".join(value.split()).strip().casefold()
    if not normalized:
        raise ValueError("tag name must not be empty")
    return normalized


def get_job_tags(session: Session, job_id: int) -> list[str]:
    """Return normalized tag names in alphabetical order."""

    statement = (
        select(JobTag.name)
        .join(JobTagLink, JobTagLink.tag_id == JobTag.id)
        .where(JobTagLink.job_id == job_id)
        .order_by(JobTag.name)
    )
    return list(session.scalars(statement))


def add_job_tag(session: Session, job_id: int, name: str) -> tuple[JobTag, bool]:
    """Attach a tag idempotently and report whether a link was newly created."""

    _require_job(session, job_id)
    normalized = normalize_tag_name(name)
    tag = session.scalar(select(JobTag).where(JobTag.name == normalized))
    if tag is None:
        tag = JobTag(name=normalized)
        session.add(tag)
        session.flush()

    existing_link = session.scalar(
        select(JobTagLink).where(JobTagLink.job_id == job_id, JobTagLink.tag_id == tag.id)
    )
    if existing_link is not None:
        return tag, False

    session.add(JobTagLink(job_id=job_id, tag_id=tag.id))
    session.flush()
    return tag, True


def remove_job_tag(session: Session, job_id: int, name: str) -> bool:
    """Remove a tag link while retaining the shared tag catalog."""

    normalized = normalize_tag_name(name)
    statement = (
        select(JobTagLink)
        .join(JobTag, JobTag.id == JobTagLink.tag_id)
        .where(JobTagLink.job_id == job_id, JobTag.name == normalized)
    )
    link = session.scalar(statement)
    if link is None:
        return False
    session.delete(link)
    session.flush()
    return True


def _require_job(session: Session, job_id: int) -> None:
    from job_finder.jobs import Job

    if session.get(Job, job_id) is None:
        raise ValueError(f"Job {job_id} does not exist.")
