"""CRUD for named, local filter presets."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from job_finder.saved_filters import (
    SavedFilterData,
    SavedFilterRecord,
    create_saved_filter,
    list_saved_filters,
    update_saved_filter,
)

router = APIRouter(prefix="/api/saved-filters", tags=["saved-filters"])


class SavedFilterResponse(BaseModel):
    id: int
    name: str
    query: dict[str, object]
    created_at: str
    updated_at: str


def get_session(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        yield session


SessionDependency = Annotated[Session, Depends(get_session)]


@router.get("", response_model=list[SavedFilterResponse])
def read_saved_filters(session: SessionDependency) -> list[SavedFilterResponse]:
    return [_response(record) for record in list_saved_filters(session)]


@router.post("", response_model=SavedFilterResponse, status_code=status.HTTP_201_CREATED)
def save_filter(payload: SavedFilterData, session: SessionDependency) -> SavedFilterResponse:
    try:
        record = create_saved_filter(session, payload)
        session.commit()
        session.refresh(record)
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um filtro com esse nome.",
        ) from error
    return _response(record)


@router.put("/{filter_id}", response_model=SavedFilterResponse)
def rename_filter(
    filter_id: int,
    payload: SavedFilterData,
    session: SessionDependency,
) -> SavedFilterResponse:
    record = session.get(SavedFilterRecord, filter_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Filtro não encontrado.")
    try:
        update_saved_filter(session, record, payload)
        session.commit()
        session.refresh(record)
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um filtro com esse nome.",
        ) from error
    return _response(record)


@router.delete("/{filter_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_filter(filter_id: int, session: SessionDependency) -> None:
    record = session.get(SavedFilterRecord, filter_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Filtro não encontrado.")
    session.delete(record)
    session.commit()


def _response(record: SavedFilterRecord) -> SavedFilterResponse:
    return SavedFilterResponse(
        id=record.id,
        name=record.name,
        query=record.query,
        created_at=record.created_at.isoformat(),
        updated_at=record.updated_at.isoformat(),
    )
