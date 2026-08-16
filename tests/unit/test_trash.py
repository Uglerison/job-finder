from datetime import datetime, timedelta, timezone
from pathlib import Path

from job_finder.database import create_database_engine, create_session_factory, run_migrations
from job_finder.jobs import JobDraft, create_job, get_job
from job_finder.trash import purge_expired_trash, restore_job, trash_job


def test_trash_is_recoverable_and_expires_after_retention(tmp_path: Path) -> None:
    run_migrations(tmp_path)
    session_factory = create_session_factory(create_database_engine(tmp_path))
    trashed_at = datetime(2026, 8, 15, tzinfo=timezone.utc)

    with session_factory.begin() as session:
        job = create_job(
            session,
            JobDraft(
                canonical_url="https://jobs.example.com/trash",
                company="Example Labs",
                title="Backend Engineer",
            ),
        )
        trash_job(session, job.id, trashed_at, retention_days=30)
        assert job.deleted_at == trashed_at.replace(tzinfo=None)
        assert job.purge_after == (trashed_at + timedelta(days=30)).replace(tzinfo=None)
        restore_job(session, job.id)
        assert job.deleted_at is None
        assert job.purge_after is None
        trash_job(session, job.id, trashed_at, retention_days=30)

    with session_factory.begin() as session:
        assert purge_expired_trash(session, trashed_at + timedelta(days=31)) == 1

    with session_factory() as session:
        assert get_job(session, job.id) is None
