"""HTTP API for notes and tags attached to jobs."""

from collections.abc import Iterator
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, StringConstraints
from sqlalchemy.orm import Session, sessionmaker

from job_finder.job_metadata import (
    JobNote,
    add_job_tag,
    create_job_note,
    delete_job_note,
    get_job_note,
    get_job_notes,
    normalize_tag_name,
    remove_job_tag,
    update_job_note,
)

router = APIRouter(prefix="/api", tags=["job-metadata"])
NoteBody = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]
TagName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


class NoteRequest(BaseModel):
    body: NoteBody


class NoteResponse(BaseModel):
    id: int
    body: str
    created_at: datetime
    updated_at: datetime


class TagRequest(BaseModel):
    name: TagName


class TagResponse(BaseModel):
    name: str


def get_session(request: Request) -> Iterator[Session]:
    session_factory: sessionmaker[Session] = request.app.state.session_factory
    with session_factory() as session:
        yield session


SessionDependency = Annotated[Session, Depends(get_session)]


@router.get("/jobs/{job_id}/notes", response_model=list[NoteResponse])
def list_notes(job_id: int, session: SessionDependency) -> list[NoteResponse]:
    notes = _notes_or_404(session, job_id)
    return [_note_response(note) for note in notes]


@router.post("/jobs/{job_id}/notes", response_model=NoteResponse, status_code=201)
def create_note(job_id: int, payload: NoteRequest, session: SessionDependency) -> NoteResponse:
    try:
        note = create_job_note(session, job_id, payload.body)
    except ValueError as error:
        raise HTTPException(status_code=404, detail="Vaga não encontrada.") from error
    session.commit()
    session.refresh(note)
    return _note_response(note)


@router.patch("/jobs/{job_id}/notes/{note_id}", response_model=NoteResponse)
def edit_note(
    job_id: int,
    note_id: int,
    payload: NoteRequest,
    session: SessionDependency,
) -> NoteResponse:
    note = get_job_note(session, job_id, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Nota não encontrada.")
    update_job_note(session, note, payload.body)
    session.commit()
    session.refresh(note)
    return _note_response(note)


@router.delete("/jobs/{job_id}/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_note(job_id: int, note_id: int, session: SessionDependency) -> Response:
    note = get_job_note(session, job_id, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Nota não encontrada.")
    delete_job_note(session, note)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/jobs/{job_id}/tags", response_model=list[TagResponse])
def list_tags(job_id: int, session: SessionDependency) -> list[TagResponse]:
    notes = _notes_or_404(session, job_id)
    del notes
    from job_finder.job_metadata import get_job_tags

    return [TagResponse(name=name) for name in get_job_tags(session, job_id)]


@router.post("/jobs/{job_id}/tags", response_model=TagResponse)
def attach_tag(
    job_id: int,
    payload: TagRequest,
    response: Response,
    session: SessionDependency,
) -> TagResponse:
    try:
        tag, created = add_job_tag(session, job_id, payload.name)
        session.commit()
    except ValueError as error:
        raise HTTPException(status_code=404, detail="Vaga não encontrada.") from error
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return TagResponse(name=tag.name)


@router.delete("/jobs/{job_id}/tags/{name}", status_code=status.HTTP_204_NO_CONTENT)
def detach_tag(job_id: int, name: str, session: SessionDependency) -> Response:
    try:
        removed = remove_job_tag(session, job_id, normalize_tag_name(name))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if not removed:
        raise HTTPException(status_code=404, detail="Tag não encontrada.")
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _notes_or_404(session: Session, job_id: int) -> list[JobNote]:
    from job_finder.jobs import get_job

    if get_job(session, job_id) is None:
        raise HTTPException(status_code=404, detail="Vaga não encontrada.")
    return get_job_notes(session, job_id)


def _note_response(note: JobNote) -> NoteResponse:
    return NoteResponse(
        id=note.id,
        body=note.body,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )
