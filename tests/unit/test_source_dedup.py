from pathlib import Path

from job_finder.database import create_database_engine, create_session_factory, run_migrations
from job_finder.source_adapters import SourceCandidate
from job_finder.source_dedup import DedupeKind, confirm_duplicate, ingest_candidate


def _candidate(
    *,
    source: str = "remoteok",
    url: str = "https://source.example/jobs/backend",
    external_id: str | None = "backend-1",
    title: str = "Backend Engineer",
    company: str = "Example Labs",
    location: str | None = "Remote",
    description: str = "Python FastAPI",
) -> SourceCandidate:
    return SourceCandidate(
        source_key=source,
        external_id=external_id,
        url=url,
        title=title,
        company=company,
        location=location,
        description=description,
    )


def test_exact_dedupe_uses_url_and_keeps_multiple_origins(tmp_path: Path) -> None:
    run_migrations(tmp_path)
    factory = create_session_factory(create_database_engine(tmp_path))
    with factory() as session:
        first = ingest_candidate(session, _candidate())
        session.commit()
        second = ingest_candidate(
            session,
            _candidate(
                source="arbeitnow",
                url="https://source.example/jobs/backend?utm_source=x",
                external_id="backend-2",
            ),
        )
        session.commit()

        assert first.kind == DedupeKind.CREATED
        assert second.kind == DedupeKind.EXACT
        assert second.reason == "canonical_url"
        assert len(second.job.origins) == 2


def test_approximate_dedupe_waits_for_confirmation_then_attaches_origin(tmp_path: Path) -> None:
    run_migrations(tmp_path)
    factory = create_session_factory(create_database_engine(tmp_path))
    with factory() as session:
        created = ingest_candidate(session, _candidate())
        session.commit()
        result = ingest_candidate(
            session,
            _candidate(
                url="https://another.example/jobs/backend",
                external_id="another-1",
                title="Backend Engineer",
                company="Example Labs",
                description="Python FastAPI and SQL",
            ),
        )
        session.commit()

        assert result.kind == DedupeKind.APPROXIMATE
        assert result.suggestion is not None
        assert result.suggestion.status == "pending"
        confirm_duplicate(session, result.suggestion)
        session.commit()
        assert result.suggestion.status == "confirmed"
        assert len(created.job.origins) == 2
