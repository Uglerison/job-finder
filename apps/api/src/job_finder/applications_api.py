"""HTTP API for applications, pipeline transitions and immutable history."""

from collections.abc import Iterator
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, StringConstraints
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from job_finder.applications import (
    Application,
    ClosingReason,
    create_application,
    get_application,
    get_application_events,
    get_application_for_job,
)
from job_finder.pipeline import (
    InvalidClosureReasonError,
    InvalidTransitionError,
    MissingClosureReasonError,
    transition_application,
)

router = APIRouter(prefix="/api", tags=["applications"])
StatusText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)]
NoteText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]


class TransitionRequest(BaseModel):
    to_status: StatusText
    note: NoteText | None = None
    correction: bool = False
    closure_reason: ClosingReason | None = None


class ApplicationEventResponse(BaseModel):
    id: int
    sequence_number: int
    kind: str
    from_status: str | None
    to_status: str
    note: str | None
    closure_reason: str | None
    occurred_at: datetime


class ApplicationResponse(BaseModel):
    id: int
    job_id: int
    current_status: str
    created_at: datetime
    updated_at: datetime
    closing_reason: str | None
    closed_at: datetime | None
    events: list[ApplicationEventResponse]


def get_session(request: Request) -> Iterator[Session]:
    session_factory: sessionmaker[Session] = request.app.state.session_factory
    with session_factory() as session:
        yield session


SessionDependency = Annotated[Session, Depends(get_session)]


@router.post("/jobs/{job_id}/application", response_model=ApplicationResponse, status_code=201)
def create_job_application(job_id: int, session: SessionDependency) -> ApplicationResponse:
    try:
        application = create_application(session, job_id)
        session.commit()
    except ValueError as error:
        session.rollback()
        if "already exists" in str(error):
            raise HTTPException(status_code=409, detail=str(error)) from error
        raise HTTPException(status_code=404, detail="Vaga não encontrada.") from error
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail="A candidatura já existe.") from error
    session.refresh(application)
    return _application_response(session, application)


@router.get("/jobs/{job_id}/application", response_model=ApplicationResponse)
def read_job_application(job_id: int, session: SessionDependency) -> ApplicationResponse:
    application = get_application_for_job(session, job_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Candidatura não encontrada.")
    return _application_response(session, application)


@router.get("/applications/{application_id}", response_model=ApplicationResponse)
def read_application(application_id: int, session: SessionDependency) -> ApplicationResponse:
    application = get_application(session, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Candidatura não encontrada.")
    return _application_response(session, application)


@router.post("/applications/{application_id}/transition", response_model=ApplicationResponse)
def move_application(
    application_id: int,
    payload: TransitionRequest,
    session: SessionDependency,
) -> ApplicationResponse:
    application = get_application(session, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Candidatura não encontrada.")
    try:
        transition_application(
            session,
            application,
            payload.to_status,  # type: ignore[arg-type]
            note=payload.note,
            correction=payload.correction,
            closure_reason=payload.closure_reason,
        )
        session.commit()
    except (InvalidTransitionError, MissingClosureReasonError, InvalidClosureReasonError) as error:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(error)) from error
    session.refresh(application)
    return _application_response(session, application)


def _application_response(session: Session, application: Application) -> ApplicationResponse:
    return ApplicationResponse(
        id=application.id,
        job_id=application.job_id,
        current_status=application.current_status,
        created_at=application.created_at,
        updated_at=application.updated_at,
        closing_reason=application.closing_reason,
        closed_at=application.closed_at,
        events=[
            ApplicationEventResponse(
                id=event.id,
                sequence_number=event.sequence_number,
                kind=event.kind,
                from_status=event.from_status,
                to_status=event.to_status,
                note=event.note,
                closure_reason=event.closure_reason,
                occurred_at=event.occurred_at,
            )
            for event in get_application_events(session, application.id)
        ],
    )
