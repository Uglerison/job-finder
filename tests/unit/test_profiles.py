from pathlib import Path

import pytest

from job_finder.database import create_database_engine, create_session_factory, run_migrations
from job_finder.profiles import (
    ImmutableProfileVersionError,
    ProfileVersion,
    create_profile,
    create_profile_version,
    get_active_profile_version,
    get_profile_versions,
)


def test_profile_versions_preserve_history_and_expose_the_active_version(
    tmp_path: Path,
) -> None:
    run_migrations(tmp_path)
    session_factory = create_session_factory(create_database_engine(tmp_path))

    with session_factory.begin() as session:
        profile = create_profile(
            session,
            criteria={"target_roles": ["Backend Engineer"], "work_model": "remote"},
        )
        profile_id = profile.id

    with session_factory.begin() as session:
        second_version = create_profile_version(
            session,
            profile_id,
            criteria={"target_roles": ["Backend Engineer"], "work_model": "hybrid"},
        )
        active_version = get_active_profile_version(session, profile_id)
        history = get_profile_versions(session, profile_id)

        assert active_version is not None
        assert active_version.id == second_version.id
        assert [version.version_number for version in history] == [1, 2]
        assert history[0].criteria == {
            "target_roles": ["Backend Engineer"],
            "work_model": "remote",
        }

    with session_factory() as session:
        first_version = session.get(ProfileVersion, history[0].id)
        assert first_version is not None
        first_version.criteria = {"target_roles": ["Changed"]}

        with pytest.raises(ImmutableProfileVersionError):
            session.commit()

        session.rollback()
