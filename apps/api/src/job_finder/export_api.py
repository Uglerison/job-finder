"""Safe local CSV and JSON exports for jobs and applications."""

import csv
import io
from collections.abc import Iterator, Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from job_finder.applications import Application, get_application_events
from job_finder.jobs import Job

router = APIRouter(prefix="/api/export", tags=["export"])


def get_session(request: Request) -> Iterator[Session]:
    session_factory: sessionmaker[Session] = request.app.state.session_factory
    with session_factory() as session:
        yield session


SessionDependency = Annotated[Session, Depends(get_session)]
StatusFilter = Annotated[str | None, Query(alias="status")]


@router.get("/jobs.json")
def export_jobs_json(
    session: SessionDependency,
    status_filter: StatusFilter = None,
) -> JSONResponse:
    jobs = _jobs(session, status_filter)
    return JSONResponse(content=[_job_payload(job) for job in jobs])


@router.get("/applications.json")
def export_applications_json(session: SessionDependency) -> JSONResponse:
    applications = _applications(session)
    return JSONResponse(content=[_application_payload(session, item) for item in applications])


@router.get("/jobs.csv")
def export_jobs_csv(
    session: SessionDependency,
    status_filter: StatusFilter = None,
) -> Response:
    jobs = _jobs(session, status_filter)
    rows = [
        ["id", "title", "company", "location", "status", "canonical_url", "created_at"],
    ] + [
        [
            job.id,
            job.title,
            job.company,
            job.location or "",
            job.status,
            job.canonical_url or "",
            _datetime_value(job.created_at),
        ]
        for job in jobs
    ]
    return _csv_response(rows, "jobs.csv")


@router.get("/applications.csv")
def export_applications_csv(session: SessionDependency) -> Response:
    applications = _applications(session)
    rows = [
        [
            "id",
            "job_id",
            "current_status",
            "closing_reason",
            "created_at",
            "updated_at",
        ],
    ] + [
        [
            application.id,
            application.job_id,
            application.current_status,
            application.closing_reason or "",
            _datetime_value(application.created_at),
            _datetime_value(application.updated_at),
        ]
        for application in applications
    ]
    return _csv_response(rows, "applications.csv")


def _jobs(session: Session, status_filter: str | None) -> list[Job]:
    statement = select(Job).order_by(Job.created_at.desc(), Job.id.desc())
    if status_filter:
        statement = statement.where(Job.status == status_filter)
    return list(session.scalars(statement))


def _applications(session: Session) -> list[Application]:
    return list(session.scalars(select(Application).order_by(Application.created_at.desc())))


def _job_payload(job: Job) -> dict[str, object]:
    return {
        "canonical_url": job.canonical_url,
        "company": job.company,
        "created_at": _datetime_value(job.created_at),
        "expires_at": _datetime_value(job.expires_at),
        "id": job.id,
        "location": job.location,
        "published_at": _datetime_value(job.published_at),
        "status": job.status,
        "title": job.title,
        "updated_at": _datetime_value(job.updated_at),
    }


def _application_payload(session: Session, application: Application) -> dict[str, object]:
    return {
        "closed_at": _datetime_value(application.closed_at),
        "closing_reason": application.closing_reason,
        "created_at": _datetime_value(application.created_at),
        "current_status": application.current_status,
        "events": [
            {
                "closure_reason": event.closure_reason,
                "from_status": event.from_status,
                "kind": event.kind,
                "note": event.note,
                "occurred_at": _datetime_value(event.occurred_at),
                "sequence_number": event.sequence_number,
                "to_status": event.to_status,
            }
            for event in get_application_events(session, application.id)
        ],
        "id": application.id,
        "job_id": application.job_id,
        "updated_at": _datetime_value(application.updated_at),
    }


def _datetime_value(value: object) -> str | None:
    return value.isoformat() if hasattr(value, "isoformat") else None


def _csv_response(rows: Sequence[Sequence[object]], filename: str) -> Response:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    for row in rows:
        writer.writerow([_neutralize_formula(value) for value in row])
    content = "\ufeff" + buffer.getvalue()
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _neutralize_formula(value: object) -> object:
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value
