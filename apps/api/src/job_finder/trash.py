"""Recoverable job deletion with retention-aware expiry."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from job_finder.applications import Application
from job_finder.job_metadata import JobNote, JobTagLink
from job_finder.jobs import Job, JobContentVersion, JobOrigin, get_job
from job_finder.preferences import DEFAULT_PREFERENCES, get_saved_preferences


class LinkedJobError(ValueError):
    """Raised when a hard delete would break a linked application."""


def trash_job(
    session: Session,
    job_id: int,
    trashed_at: datetime | None = None,
    *,
    retention_days: int | None = None,
) -> Job:
    """Soft-delete a job and calculate its recoverable retention deadline."""

    job = get_job(session, job_id)
    if job is None:
        raise ValueError(f"Job {job_id} does not exist.")
    now = _utc_naive(trashed_at or datetime.now(timezone.utc))
    if retention_days is None:
        preferences = get_saved_preferences(session)
        retention_days = (
            preferences.retention_days if preferences else DEFAULT_PREFERENCES.retention_days
        )
    job.deleted_at = job.deleted_at or now
    job.purge_after = job.purge_after or now + timedelta(days=retention_days)
    session.flush()
    return job


def restore_job(session: Session, job_id: int) -> Job:
    """Restore a soft-deleted job without changing its application history."""

    job = get_job(session, job_id)
    if job is None:
        raise ValueError(f"Job {job_id} does not exist.")
    job.deleted_at = None
    job.purge_after = None
    session.flush()
    return job


def purge_expired_trash(session: Session, now: datetime | None = None) -> int:
    """Permanently remove expired jobs that have no linked application."""

    cutoff = _utc_naive(now or datetime.now(timezone.utc))
    jobs = session.scalars(
        select(Job).where(Job.deleted_at.is_not(None), Job.purge_after <= cutoff)
    ).all()
    purged = 0
    for job in jobs:
        if session.scalar(select(Application.id).where(Application.job_id == job.id)) is not None:
            continue
        session.delete(job)
        purged += 1
    session.flush()
    return purged


def hard_delete_job(session: Session, job_id: int) -> None:
    """Permanently delete only an unlinked job after explicit confirmation."""

    job = get_job(session, job_id)
    if job is None:
        raise ValueError(f"Job {job_id} does not exist.")
    if session.scalar(select(Application.id).where(Application.job_id == job.id)) is not None:
        raise LinkedJobError("Não é possível excluir uma vaga com candidatura vinculada.")
    origin_ids = select(JobOrigin.id).where(JobOrigin.job_id == job.id)
    session.execute(delete(JobContentVersion).where(JobContentVersion.origin_id.in_(origin_ids)))
    session.execute(delete(JobOrigin).where(JobOrigin.job_id == job.id))
    session.execute(delete(JobNote).where(JobNote.job_id == job.id))
    session.execute(delete(JobTagLink).where(JobTagLink.job_id == job.id))
    session.delete(job)
    session.flush()


def _utc_naive(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Trash timestamps must include a timezone.")
    return value.astimezone(timezone.utc).replace(tzinfo=None)
