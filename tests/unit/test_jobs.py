from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from job_finder.database import create_database_engine, create_session_factory, run_migrations
from job_finder.jobs import (
    ImmutableJobContentVersionError,
    JobContentDraft,
    JobDraft,
    JobOriginDraft,
    add_job_content_version,
    add_job_origin,
    create_job,
    get_job,
    get_job_content_versions,
    get_job_origins,
)


def test_job_preserves_normalized_data_multiple_origins_and_content_history(
    tmp_path: Path,
) -> None:
    run_migrations(tmp_path)
    session_factory = create_session_factory(create_database_engine(tmp_path))
    first_capture = datetime(2026, 8, 15, 12, tzinfo=timezone.utc)
    second_capture = first_capture + timedelta(days=2)

    with session_factory.begin() as session:
        job = create_job(
            session,
            JobDraft(
                canonical_url="https://careers.example/jobs/backend-42",
                title="Backend Engineer",
                company="Example Labs",
                location="São Paulo, SP",
            ),
        )
        company_origin = add_job_origin(
            session,
            job.id,
            JobOriginDraft(
                source="company-careers",
                external_id="backend-42",
                url="https://careers.example/jobs/backend-42",
            ),
        )
        aggregator_origin = add_job_origin(
            session,
            job.id,
            JobOriginDraft(
                source="aggregator",
                external_id="agg-987",
                url="https://jobs.example/vagas/agg-987",
            ),
        )
        first_version = add_job_content_version(
            session,
            company_origin.id,
            JobContentDraft(
                raw_content="<article>Backend Engineer — primeira publicação</article>",
                content_type="text/html",
                captured_at=first_capture,
                valid_from=first_capture,
                valid_until=second_capture,
            ),
        )
        second_version = add_job_content_version(
            session,
            company_origin.id,
            JobContentDraft(
                raw_content="<article>Backend Engineer — salário atualizado</article>",
                content_type="text/html",
                captured_at=second_capture,
                valid_from=second_capture,
            ),
        )
        add_job_content_version(
            session,
            aggregator_origin.id,
            JobContentDraft(
                raw_content='{"title":"Backend Engineer","source":"aggregator"}',
                content_type="application/json",
                captured_at=first_capture,
                valid_from=first_capture,
            ),
        )

        assert job.id is not None
        assert company_origin.id is not None
        assert aggregator_origin.id is not None
        assert first_version.version_number == 1
        assert second_version.version_number == 2

    with session_factory() as session:
        persisted_job = get_job(session, job.id)
        origins = get_job_origins(session, job.id)
        versions = get_job_content_versions(session, company_origin.id)

        assert persisted_job is not None
        assert persisted_job.canonical_url == "https://careers.example/jobs/backend-42"
        assert persisted_job.title == "Backend Engineer"
        assert [origin.source for origin in origins] == ["company-careers", "aggregator"]
        assert [version.version_number for version in versions] == [1, 2]
        assert versions[0].raw_content.endswith("primeira publicação</article>")
        # SQLite returns timezone-aware values as naive UTC datetimes.
        assert versions[0].valid_until == second_capture.replace(tzinfo=None)
        assert versions[1].valid_until is None


def test_job_content_versions_are_immutable(tmp_path: Path) -> None:
    run_migrations(tmp_path)
    session_factory = create_session_factory(create_database_engine(tmp_path))

    with session_factory.begin() as session:
        job = create_job(
            session,
            JobDraft(
                canonical_url="https://example.com/jobs/1",
                title="Data Engineer",
                company="Example",
            ),
        )
        origin = add_job_origin(
            session,
            job.id,
            JobOriginDraft(source="manual", url="https://example.com/jobs/1"),
        )
        version = add_job_content_version(
            session,
            origin.id,
            JobContentDraft(
                raw_content="descrição original",
                captured_at=datetime.now(timezone.utc),
                valid_from=datetime.now(timezone.utc),
            ),
        )

    with session_factory() as session:
        persisted_version = session.get(type(version), version.id)
        assert persisted_version is not None
        persisted_version.raw_content = "tentativa de alteração"

        with pytest.raises(ImmutableJobContentVersionError):
            session.commit()


def test_job_content_rejects_an_expiration_before_its_validity_start() -> None:
    with pytest.raises(ValueError, match="valid_until"):
        JobContentDraft(
            raw_content="descrição",
            captured_at=datetime(2026, 8, 15, tzinfo=timezone.utc),
            valid_from=datetime(2026, 8, 15, tzinfo=timezone.utc),
            valid_until=datetime(2026, 8, 14, tzinfo=timezone.utc),
        )
