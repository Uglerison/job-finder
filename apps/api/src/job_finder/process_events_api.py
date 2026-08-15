"""HTTP API for interviews, challenges and application deadlines."""

from collections.abc import Iterator
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session, sessionmaker

from job_finder.applications import get_application
from job_finder.process_events import (
    EventConflictError,
    EventTimeError,
    ProcessEvent,
    ProcessEventDraft,
    create_process_event,
    get_process_events,
)

router = APIRouter(prefix="/api", tags=["process-events"])
EventKind = Literal["interview", "challenge", "deadline"]


class ProcessEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: EventKind
    title: str = Field(min_length=1, max_length=240)
    starts_at: datetime
    ends_at: datetime | None = None
    participants: list[str] = Field(default_factory=list, max_length=20)
    link: str | None = Field(default=None, max_length=2048)
    notes: str | None = Field(default=None, max_length=4000)
    timezone_name: str | None = Field(default=None, max_length=64)

    @field_validator("starts_at", "ends_at")
    @classmethod
    def datetime_must_include_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Event timestamps must include a timezone.")
        return value


class ProcessEventResponse(BaseModel):
    id: int
    application_id: int
    kind: str
    title: str
    starts_at: datetime
    ends_at: datetime | None
    timezone_name: str
    participants: list[str]
    link: str | None
    notes: str | None
    status: str


def get_session(request: Request) -> Iterator[Session]:
    session_factory: sessionmaker[Session] = request.app.state.session_factory
    with session_factory() as session:
        yield session


SessionDependency = Annotated[Session, Depends(get_session)]


@router.get(
    "/applications/{application_id}/events",
    response_model=list[ProcessEventResponse],
)
def list_process_events(
    application_id: int,
    session: SessionDependency,
) -> list[ProcessEventResponse]:
    if get_application(session, application_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Candidatura não encontrada."
        )
    return [_event_response(event) for event in get_process_events(session, application_id)]


@router.post(
    "/applications/{application_id}/events",
    response_model=ProcessEventResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_application_event(
    application_id: int,
    payload: ProcessEventRequest,
    session: SessionDependency,
) -> ProcessEventResponse:
    try:
        event = create_process_event(
            session,
            application_id,
            ProcessEventDraft(
                kind=payload.kind,
                title=payload.title,
                starts_at=payload.starts_at,
                ends_at=payload.ends_at,
                participants=payload.participants,
                link=payload.link,
                notes=payload.notes,
                timezone_name=payload.timezone_name,
            ),
        )
        session.commit()
    except ValueError as error:
        session.rollback()
        if isinstance(error, EventConflictError):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
        if isinstance(error, EventTimeError):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(error),
            ) from error
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidatura não encontrada.",
        ) from error
    return _event_response(event)


def _event_response(event: ProcessEvent) -> ProcessEventResponse:
    return ProcessEventResponse(
        id=event.id,
        application_id=event.application_id,
        kind=event.kind,
        title=event.title,
        starts_at=event.starts_at,
        ends_at=event.ends_at,
        timezone_name=event.timezone_name,
        participants=event.participants,
        link=event.link,
        notes=event.notes,
        status=event.status,
    )
