from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from job_finder.applications import create_application
from job_finder.database import create_database_engine, create_session_factory, run_migrations
from job_finder.jobs import JobDraft, create_job
from job_finder.process_events import (
    EventConflictError,
    EventTimeError,
    ProcessEventDraft,
    create_process_event,
    is_event_overdue,
)


def _session_factory(tmp_path: Path):
    run_migrations(tmp_path)
    return create_session_factory(create_database_engine(tmp_path))


def test_process_event_keeps_timezone_and_detects_overdue_deadline(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    starts_at = datetime(2026, 8, 15, 10, tzinfo=timezone.utc)
    ends_at = starts_at + timedelta(hours=1)

    with session_factory.begin() as session:
        job = create_job(
            session,
            JobDraft(
                canonical_url="https://jobs.example.com/event",
                company="Example Labs",
                title="Backend Engineer",
            ),
        )
        application = create_application(session, job.id)
        event = create_process_event(
            session,
            application.id,
            ProcessEventDraft(
                kind="interview",
                title="Entrevista técnica",
                starts_at=starts_at,
                ends_at=ends_at,
                participants=["ana@example.com"],
                link="https://meet.example.com/room",
            ),
        )

    assert event.application_id == application.id
    assert event.starts_at == starts_at.replace(tzinfo=None)
    assert event.participants == ["ana@example.com"]
    assert is_event_overdue(event, ends_at + timedelta(minutes=1))


def test_process_event_rejects_naive_time_and_overlapping_event(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    starts_at = datetime(2026, 8, 15, 10, tzinfo=timezone.utc)

    with session_factory.begin() as session:
        job = create_job(
            session,
            JobDraft(
                canonical_url="https://jobs.example.com/event-conflict",
                company="Example Labs",
                title="Data Engineer",
            ),
        )
        application = create_application(session, job.id)
        with pytest.raises(EventTimeError, match="timezone"):
            create_process_event(
                session,
                application.id,
                ProcessEventDraft(
                    kind="deadline",
                    title="Prazo",
                    starts_at=starts_at.replace(tzinfo=None),
                ),
            )

        create_process_event(
            session,
            application.id,
            ProcessEventDraft(
                kind="interview",
                title="Entrevista",
                starts_at=starts_at,
                ends_at=starts_at + timedelta(hours=1),
            ),
        )
        with pytest.raises(EventConflictError, match="conflict"):
            create_process_event(
                session,
                application.id,
                ProcessEventDraft(
                    kind="challenge",
                    title="Desafio",
                    starts_at=starts_at + timedelta(minutes=30),
                    ends_at=starts_at + timedelta(hours=2),
                ),
            )
