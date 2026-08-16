from datetime import timezone
from pathlib import Path

import pytest

from job_finder.applications import (
    ImmutableApplicationEventError,
    create_application,
    get_application_events,
)
from job_finder.database import create_database_engine, create_session_factory, run_migrations
from job_finder.jobs import JobDraft, create_job


def test_application_is_unique_per_job_and_events_are_immutable(tmp_path: Path) -> None:
    run_migrations(tmp_path)
    session_factory = create_session_factory(create_database_engine(tmp_path))

    with session_factory.begin() as session:
        job = create_job(
            session,
            JobDraft(
                canonical_url="https://jobs.example.com/application",
                company="Example Labs",
                title="Backend Engineer",
            ),
        )
        application = create_application(session, job.id)
        with pytest.raises(ValueError, match="already exists"):
            create_application(session, job.id)
        events = get_application_events(session, application.id)

    assert application.current_status == "found"
    assert len(events) == 1
    assert events[0].to_status == "found"
    assert events[0].occurred_at.tzinfo is None or isinstance(
        events[0].occurred_at.tzinfo,
        timezone,
    )

    with session_factory() as session:
        event = get_application_events(session, application.id)[0]
        event.note = "alterado"
        with pytest.raises(ImmutableApplicationEventError):
            session.commit()
