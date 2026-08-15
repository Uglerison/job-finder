"""HTTP contracts for manual job intake and auditable source evidence."""

from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from job_finder.jobs import (
    Job,
    JobContentDraft,
    JobContentVersion,
    JobOrigin,
    JobOriginDraft,
    add_job_content_version,
    add_job_origin,
    create_job,
    get_job_content_versions,
    get_job_origins,
)
from job_finder.normalization import RawJobData, normalize_job, normalize_url

router = APIRouter(prefix="/api", tags=["jobs"])


class ManualJobRequest(BaseModel):
    """Fields required to create a local job from a user-provided listing."""

    model_config = ConfigDict(extra="forbid")

    canonical_url: str = Field(min_length=1, max_length=2048)
    title: str = Field(min_length=1, max_length=240)
    company: str = Field(min_length=1, max_length=240)
    location: str | None = Field(default=None, max_length=240)
    published_at: datetime | None = None
    expires_at: datetime | None = None
    raw_content: str = Field(min_length=1)

    @field_validator("canonical_url")
    @classmethod
    def canonical_url_must_be_http(cls, value: str) -> str:
        normalized = normalize_url(value)
        if normalized is None:
            raise ValueError("canonical_url must use an http or https scheme")
        return normalized


class JobOriginResponse(BaseModel):
    id: int
    source: str
    external_id: str | None
    url: str | None


class JobContentVersionResponse(BaseModel):
    id: int
    version_number: int
    raw_content: str
    content_type: str
    captured_at: datetime
    valid_from: datetime
    valid_until: datetime | None


class JobResponse(BaseModel):
    id: int
    canonical_url: str | None
    title: str
    company: str
    location: str | None
    published_at: datetime | None
    expires_at: datetime | None
    status: str
    status_label: str
    created_at: datetime
    updated_at: datetime
    origins: list[JobOriginResponse]
    content_versions: list[JobContentVersionResponse]


def get_session(request: Request) -> Iterator[Session]:
    """Provide one transaction-capable local session per request."""

    session_factory: sessionmaker[Session] = request.app.state.session_factory
    with session_factory() as session:
        yield session


SessionDependency = Annotated[Session, Depends(get_session)]


@router.post("/jobs", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_manual_job(
    payload: ManualJobRequest,
    session: SessionDependency,
) -> JobResponse:
    """Create a normalized found job and preserve the submitted listing exactly."""

    normalized = normalize_job(
        RawJobData(
            canonical_url=payload.canonical_url,
            title=payload.title,
            company=payload.company,
            location=payload.location,
            published_at=payload.published_at,
            expires_at=payload.expires_at,
        ),
    )
    now = datetime.now(timezone.utc)

    try:
        job = create_job(session, normalized)
        origin = add_job_origin(
            session,
            job.id,
            JobOriginDraft(source="manual", url=normalized.canonical_url),
        )
        add_job_content_version(
            session,
            origin.id,
            _content_draft(payload.raw_content, now),
        )
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma vaga com esta URL canônica.",
        ) from error

    session.refresh(job)
    return _job_response(session, job)


def _content_draft(raw_content: str, now: datetime) -> JobContentDraft:
    return JobContentDraft(
        raw_content=raw_content,
        content_type="text/html" if "<" in raw_content else "text/plain",
        captured_at=now,
        valid_from=now,
    )


def _job_response(session: Session, job: Job) -> JobResponse:
    origins = get_job_origins(session, job.id)
    content_versions = [
        version for origin in origins for version in get_job_content_versions(session, origin.id)
    ]
    return JobResponse(
        id=job.id,
        canonical_url=job.canonical_url,
        title=job.title,
        company=job.company,
        location=job.location,
        published_at=job.published_at,
        expires_at=job.expires_at,
        status=job.status,
        status_label=_status_label(job.status),
        created_at=job.created_at,
        updated_at=job.updated_at,
        origins=[_origin_response(origin) for origin in origins],
        content_versions=[_content_response(version) for version in content_versions],
    )


def _origin_response(origin: JobOrigin) -> JobOriginResponse:
    return JobOriginResponse(
        id=origin.id,
        source=origin.source,
        external_id=origin.external_id,
        url=origin.url,
    )


def _content_response(version: JobContentVersion) -> JobContentVersionResponse:
    return JobContentVersionResponse(
        id=version.id,
        version_number=version.version_number,
        raw_content=version.raw_content,
        content_type=version.content_type,
        captured_at=version.captured_at,
        valid_from=version.valid_from,
        valid_until=version.valid_until,
    )


def _status_label(value: str) -> str:
    return {
        "found": "ENCONTRADA",
        "pending": "EM ESPERA",
        "rejected": "REJEITADA",
        "applied": "APLICADA",
    }.get(value, value.upper())
