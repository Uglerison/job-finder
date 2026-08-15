"""Versioned persistence model and repository operations for job-search profiles."""

from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, UniqueConstraint, event, func, select
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Mapped, Mapper, Session, mapped_column, relationship

from job_finder.database import Base


class ImmutableProfileVersionError(RuntimeError):
    """Raised when code attempts to modify a historical profile version."""


class Profile(Base):
    """One logical job-search profile with immutable versions over time."""

    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    versions: Mapped[list["ProfileVersion"]] = relationship(
        back_populates="profile",
        order_by="ProfileVersion.version_number",
    )


class ProfileVersion(Base):
    """An immutable snapshot of a profile's criteria."""

    __tablename__ = "profile_versions"
    __table_args__ = (UniqueConstraint("profile_id", "version_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    criteria: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    profile: Mapped[Profile] = relationship(back_populates="versions")


@event.listens_for(ProfileVersion, "before_update")
def prevent_profile_version_update(
    _mapper: Mapper[ProfileVersion],
    _connection: Connection,
    _target: ProfileVersion,
) -> None:
    """Keep historical criteria immutable once their version is persisted."""

    raise ImmutableProfileVersionError("Profile versions are immutable. Create a new version.")


@event.listens_for(ProfileVersion, "before_delete")
def prevent_profile_version_delete(
    _mapper: Mapper[ProfileVersion],
    _connection: Connection,
    _target: ProfileVersion,
) -> None:
    """Preserve profile history instead of allowing a version to disappear."""

    raise ImmutableProfileVersionError("Profile versions cannot be deleted.")


def create_profile(session: Session, criteria: Mapping[str, object]) -> Profile:
    """Create a logical profile together with its first immutable version."""

    profile = Profile()
    session.add(profile)
    session.flush()
    _create_profile_version(session, profile, criteria)
    return profile


def create_profile_version(
    session: Session,
    profile_id: int,
    criteria: Mapping[str, object],
) -> ProfileVersion:
    """Append a new immutable criteria snapshot to an existing profile."""

    profile = session.get(Profile, profile_id)
    if profile is None:
        raise ValueError(f"Profile {profile_id} does not exist.")

    return _create_profile_version(session, profile, criteria)


def get_active_profile_version(session: Session, profile_id: int) -> ProfileVersion | None:
    """Return the newest profile version, which is the profile's active version."""

    statement = (
        select(ProfileVersion)
        .where(ProfileVersion.profile_id == profile_id)
        .order_by(ProfileVersion.version_number.desc())
        .limit(1)
    )
    return session.scalar(statement)


def get_profile_versions(session: Session, profile_id: int) -> list[ProfileVersion]:
    """Return a profile's complete immutable history in creation order."""

    statement = (
        select(ProfileVersion)
        .where(ProfileVersion.profile_id == profile_id)
        .order_by(ProfileVersion.version_number)
    )
    return list(session.scalars(statement))


def _create_profile_version(
    session: Session,
    profile: Profile,
    criteria: Mapping[str, object],
) -> ProfileVersion:
    current_version = session.scalar(
        select(func.max(ProfileVersion.version_number)).where(
            ProfileVersion.profile_id == profile.id
        )
    )
    profile_version = ProfileVersion(
        profile=profile,
        version_number=(current_version or 0) + 1,
        criteria=deepcopy(dict(criteria)),
    )
    session.add(profile_version)
    session.flush()
    return profile_version
