"""HTTP routes for reading and versioning the local job-search profile."""

from collections.abc import Iterator
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session, sessionmaker

from job_finder.profile_criteria import ProfileCriteria
from job_finder.profiles import (
    ProfileVersion,
    create_profile,
    create_profile_version,
    get_active_profile_version,
    get_current_profile_version,
    get_profile_versions,
)

router = APIRouter(prefix="/api", tags=["profile"])


class ProfileVersionResponse(BaseModel):
    """The active profile snapshot returned by the local API."""

    profile_id: int
    version_number: int
    criteria: ProfileCriteria
    created_at: datetime


def get_session(request: Request) -> Iterator[Session]:
    """Provide one transaction-capable database session for an API request."""

    session_factory: sessionmaker[Session] = request.app.state.session_factory
    with session_factory() as session:
        yield session


SessionDependency = Annotated[Session, Depends(get_session)]


@router.get("/profile", response_model=ProfileVersionResponse | None)
def read_profile(session: SessionDependency) -> ProfileVersionResponse | None:
    """Read the current profile or explicitly return an empty first-run state."""

    profile_version = get_current_profile_version(session)
    return _profile_response(profile_version) if profile_version is not None else None


@router.get("/profile/versions", response_model=list[ProfileVersionResponse])
def read_profile_versions(session: SessionDependency) -> list[ProfileVersionResponse]:
    """Read every immutable version of the local profile in creation order."""

    current_version = get_current_profile_version(session)
    if current_version is None:
        return []

    versions = get_profile_versions(session, current_version.profile_id)
    return [_profile_response(version) for version in versions]


@router.put("/profile", response_model=ProfileVersionResponse)
def replace_profile(
    criteria: ProfileCriteria,
    session: SessionDependency,
) -> ProfileVersionResponse:
    """Create the first profile or append a new immutable validated version."""

    current_version = get_current_profile_version(session)
    persisted_criteria = criteria.model_dump(mode="json")
    if current_version is None:
        profile = create_profile(session, persisted_criteria)
        profile_version = get_active_profile_version(session, profile.id)
        if profile_version is None:
            raise RuntimeError("The first profile version could not be created.")
    else:
        profile_version = create_profile_version(
            session,
            current_version.profile_id,
            persisted_criteria,
        )

    session.commit()
    session.refresh(profile_version)
    return _profile_response(profile_version)


def _profile_response(profile_version: ProfileVersion) -> ProfileVersionResponse:
    return ProfileVersionResponse(
        profile_id=profile_version.profile_id,
        version_number=profile_version.version_number,
        criteria=ProfileCriteria.model_validate(profile_version.criteria),
        created_at=profile_version.created_at,
    )
