"""Explicit local API action for one transient structured job analysis."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session, sessionmaker

from job_finder.ai_analysis import StructuredJobAnalysis
from job_finder.ai_extraction import JobAnalysisError, analyze_job_content
from job_finder.ai_prompts import AnalysisMode
from job_finder.ai_settings_api import (
    AiSettingsDependency,
    OpenAiStructuredClientDependency,
    translate_openai_error,
    translate_vault_error,
)
from job_finder.jobs import JobContentVersion, get_job, get_job_content_versions, get_job_origins
from job_finder.openai_client import OpenAiClientError
from job_finder.profile_criteria import ProfileCriteria
from job_finder.profiles import get_current_profile_version
from job_finder.secret_store import SecretStoreError

router = APIRouter(prefix="/api", tags=["ai-analysis"])


class JobAnalysisRequest(BaseModel):
    """An explicit analysis mode; detailed reasoning is never the default."""

    model_config = ConfigDict(extra="forbid")

    mode: AnalysisMode = "batch"


class JobAnalysisResponse(BaseModel):
    """Transient validated analysis; persistence is intentionally a later concern."""

    job_id: int
    job_content_version_id: int
    analysis: StructuredJobAnalysis
    model: str
    prompt_version: str


def get_session(request: Request) -> Iterator[Session]:
    """Provide one local database session for an explicit analysis request."""

    session_factory: sessionmaker[Session] = request.app.state.session_factory
    with session_factory() as session:
        yield session


SessionDependency = Annotated[Session, Depends(get_session)]


@router.post("/jobs/{job_id}/analysis", response_model=JobAnalysisResponse)
def analyze_job(
    job_id: int,
    session: SessionDependency,
    settings: AiSettingsDependency,
    client: OpenAiStructuredClientDependency,
    payload: JobAnalysisRequest | None = None,
) -> JobAnalysisResponse:
    """Analyze the newest captured job content, only when key and profile are ready."""

    job = get_job(session, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vaga não encontrada.")
    if job.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Restaure a vaga antes de solicitar uma análise por IA.",
        )

    profile_version = get_current_profile_version(session)
    if profile_version is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Configure o perfil antes de analisar vagas com IA.",
        )
    latest_content = _latest_job_content(session, job_id)
    if latest_content is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A vaga não possui conteúdo para análise.",
        )

    try:
        api_key = settings.get_api_key()
    except SecretStoreError as error:
        raise translate_vault_error(error) from error
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Configure e desbloqueie a chave OpenAI para analisar vagas.",
        )

    try:
        execution = analyze_job_content(
            client,
            api_key,
            profile=ProfileCriteria.model_validate(profile_version.criteria),
            title=job.title,
            company=job.company,
            location=job.location,
            raw_content=latest_content.raw_content,
            mode=payload.mode if payload is not None else "batch",
        )
    except JobAnalysisError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
    except OpenAiClientError as error:
        raise translate_openai_error(error) from error

    return JobAnalysisResponse(
        job_id=job.id,
        job_content_version_id=latest_content.id,
        analysis=execution.analysis,
        model=execution.model,
        prompt_version=execution.prompt_version,
    )


def _latest_job_content(session: Session, job_id: int) -> JobContentVersion | None:
    """Select the newest source snapshot deterministically across all job origins."""

    versions = [
        version
        for origin in get_job_origins(session, job_id)
        for version in get_job_content_versions(session, origin.id)
    ]
    return max(versions, key=lambda version: (version.captured_at, version.id), default=None)
