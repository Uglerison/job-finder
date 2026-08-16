from datetime import datetime, timezone
from pathlib import Path

import pytest

from job_finder.database import create_database_engine, create_session_factory, run_migrations
from job_finder.job_analyses import (
    ImmutableJobAnalysisVersionError,
    JobAnalysisVersionDraft,
    create_job_analysis_version,
    get_job_analysis_versions,
)
from job_finder.jobs import (
    JobContentDraft,
    JobDraft,
    JobOriginDraft,
    add_job_content_version,
    add_job_origin,
    create_job,
)
from job_finder.profiles import create_profile, get_active_profile_version


def make_draft(
    profile_version_id: int,
    job_id: int,
    content_version_id: int,
) -> JobAnalysisVersionDraft:
    return JobAnalysisVersionDraft(
        profile_version_id=profile_version_id,
        job_id=job_id,
        job_content_version_id=content_version_id,
        model="gpt-5.6-luna",
        prompt_version="2026-08-15.1",
        analysis={"extraction": {"title": "Data Analyst"}},
        fit={"score": 72},
        explanation={"supported_evidence": []},
    )


def test_job_analysis_versions_are_append_only_and_keep_the_exact_provenance(
    tmp_path: Path,
) -> None:
    run_migrations(tmp_path)
    session_factory = create_session_factory(create_database_engine(tmp_path))
    now = datetime.now(timezone.utc)

    with session_factory() as session:
        profile = create_profile(
            session,
            {
                "target_roles": ["Data Analyst"],
                "skills": ["SQL"],
                "languages": [],
                "salary_expectation": None,
                "weights": {"skills": 100},
                "restrictions": {"work_models": ["remote"]},
            },
        )
        profile_version = get_active_profile_version(session, profile.id)
        assert profile_version is not None
        job = create_job(
            session,
            JobDraft(title="Data Analyst", company="Example Labs", status="found"),
        )
        origin = add_job_origin(session, job.id, JobOriginDraft(source="manual"))
        content = add_job_content_version(
            session,
            origin.id,
            JobContentDraft(
                raw_content="Strong SQL skills are required.",
                captured_at=now,
                valid_from=now,
            ),
        )

        first = create_job_analysis_version(
            session,
            make_draft(profile_version.id, job.id, content.id),
        )
        create_job_analysis_version(
            session,
            make_draft(profile_version.id, job.id, content.id),
        )
        session.commit()

        versions = get_job_analysis_versions(session, job.id)
        assert [item.version_number for item in versions] == [1, 2]
        assert first.profile_version_id == profile_version.id
        assert first.job_content_version_id == content.id
        assert first.model == "gpt-5.6-luna"
        assert first.prompt_version == "2026-08-15.1"
        assert first.analysis == {"extraction": {"title": "Data Analyst"}}

        first.model = "another-model"
        with pytest.raises(ImmutableJobAnalysisVersionError):
            session.flush()
