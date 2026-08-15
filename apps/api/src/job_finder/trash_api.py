"""HTTP API for recoverable job trash and explicit permanent deletion."""

from collections.abc import Iterator
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from job_finder.jobs import Job
from job_finder.trash import (
    LinkedJobError,
    hard_delete_job,
    purge_expired_trash,
    restore_job,
    trash_job,
)

router = APIRouter(prefix="/api", tags=["trash"])


class TrashItemResponse(BaseModel):
    id: int
    title: str
    company: str
    status: str
    deleted_at: datetime
    purge_after: datetime


class RestoreResponse(BaseModel):
    id: int
    title: str
    company: str
    status: str
    deleted_at: datetime | None
    purge_after: datetime | None


class PurgeResponse(BaseModel):
    purged: int


def get_session(request: Request) -> Iterator[Session]:
    session_factory: sessionmaker[Session] = request.app.state.session_factory
    with session_factory() as session:
        yield session


SessionDependency = Annotated[Session, Depends(get_session)]


@router.get("/trash", response_model=list[TrashItemResponse])
def list_trash(session: SessionDependency) -> list[TrashItemResponse]:
    jobs = session.scalars(
        select(Job)
        .where(Job.deleted_at.is_not(None), Job.purge_after.is_not(None))
        .order_by(Job.deleted_at.desc(), Job.id.desc())
    ).all()
    return [_trash_response(job) for job in jobs]


@router.post("/jobs/{job_id}/trash", response_model=TrashItemResponse)
def move_job_to_trash(job_id: int, session: SessionDependency) -> TrashItemResponse:
    try:
        job = trash_job(session, job_id)
        session.commit()
    except ValueError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vaga não encontrada."
        ) from error
    session.refresh(job)
    return _trash_response(job)


@router.post("/jobs/{job_id}/restore", response_model=RestoreResponse)
def restore_trashed_job(job_id: int, session: SessionDependency) -> RestoreResponse:
    try:
        job = restore_job(session, job_id)
        session.commit()
    except ValueError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vaga não encontrada."
        ) from error
    session.refresh(job)
    return RestoreResponse(
        id=job.id,
        title=job.title,
        company=job.company,
        status=job.status,
        deleted_at=job.deleted_at,
        purge_after=job.purge_after,
    )


@router.post("/trash/purge", response_model=PurgeResponse)
def purge_trash(session: SessionDependency) -> PurgeResponse:
    purged = purge_expired_trash(session)
    session.commit()
    return PurgeResponse(purged=purged)


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def permanently_delete_job(
    job_id: int,
    session: SessionDependency,
    confirm: bool = Query(default=False),
) -> Response:
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirme a exclusão definitiva com confirm=true.",
        )
    try:
        hard_delete_job(session, job_id)
        session.commit()
    except LinkedJobError as error:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except ValueError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vaga não encontrada."
        ) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _trash_response(job: Job) -> TrashItemResponse:
    if job.deleted_at is None or job.purge_after is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A vaga não está na lixeira."
        )
    return TrashItemResponse(
        id=job.id,
        title=job.title,
        company=job.company,
        status=job.status,
        deleted_at=job.deleted_at,
        purge_after=job.purge_after,
    )
