from datetime import timedelta
from pathlib import Path

from job_finder.database import create_database_engine, create_session_factory, run_migrations
from job_finder.scheduler import PersistentScheduler
from job_finder.source_models import (
    SourceConfigRecord,
    create_search_run,
    ensure_default_sources,
    utc_now,
)


def test_scheduler_recovers_inflight_runs_and_respects_disabled_automation(tmp_path: Path) -> None:
    run_migrations(tmp_path)
    factory = create_session_factory(create_database_engine(tmp_path))
    with factory() as session:
        sources = ensure_default_sources(session)
        source = sources[0]
        source.schedule_enabled = False
        source.next_run_at = utc_now() - timedelta(minutes=1)
        run = create_search_run(session, source, {})
        run.status = "running"
        session.commit()

        scheduler = PersistentScheduler()
        recovered = scheduler.recover_interrupted_runs(session)
        assert recovered == 1
        assert run.status == "failed"
        assert run.error_message is not None
        assert scheduler.due(session) == []


def test_scheduler_returns_due_enabled_source(tmp_path: Path) -> None:
    run_migrations(tmp_path)
    factory = create_session_factory(create_database_engine(tmp_path))
    with factory() as session:
        source = ensure_default_sources(session)[0]
        source.schedule_enabled = True
        source.next_run_at = utc_now() - timedelta(minutes=1)
        session.commit()

        assert scheduler_keys(PersistentScheduler().due(session)) == [source.source_key]


def scheduler_keys(records: list[SourceConfigRecord]) -> list[str]:
    return [record.source_key for record in records]
