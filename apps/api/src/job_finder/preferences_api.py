"""HTTP routes for general local preferences."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session, sessionmaker

from job_finder.preferences import (
    DEFAULT_PREFERENCES,
    PreferencesData,
    get_saved_preferences,
    preferences_from_record,
    save_preferences,
)

router = APIRouter(prefix="/api/preferences", tags=["preferences"])


def get_session(request: Request) -> Iterator[Session]:
    """Provide a transaction-capable database session for preferences."""

    session_factory: sessionmaker[Session] = request.app.state.session_factory
    with session_factory() as session:
        yield session


SessionDependency = Annotated[Session, Depends(get_session)]


@router.get("", response_model=PreferencesData)
def read_preferences(session: SessionDependency) -> PreferencesData:
    """Return saved preferences or stable local defaults on first run."""

    record = get_saved_preferences(session)
    return preferences_from_record(record) if record is not None else DEFAULT_PREFERENCES


@router.put("", response_model=PreferencesData)
def replace_preferences(
    preferences: PreferencesData,
    session: SessionDependency,
) -> PreferencesData:
    """Persist validated preferences in the singleton local row."""

    record = save_preferences(session, preferences)
    session.commit()
    session.refresh(record)
    return preferences_from_record(record)
