"""Explicit local API action for one transient structured job analysis."""

from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session, sessionmaker

from job_finder.ai_analysis import StructuredJobAnalysis
from job_finder.ai_budget import (
    AI_BUDGET_LOCK,
    BudgetConfig,
    BudgetState,
    evaluate_budget,
    pricing_from_settings,
)
from job_finder.ai_cache import AnalysisPromptCache
from job_finder.ai_explanation import JobExplanation, build_explanation
from job_finder.ai_extraction import JobAnalysisError, analyze_job_content
from job_finder.ai_fallback import build_fallback_analysis
from job_finder.ai_prompts import AnalysisMode
from job_finder.ai_scoring import HybridFitScore, calculate_hybrid_fit
from job_finder.ai_settings_api import (
    AiSettingsDependency,
    OpenAiStructuredClientDependency,
    translate_openai_error,
    translate_vault_error,
)
from job_finder.ai_usage import AnalysisUsage, usage_from_response
from job_finder.job_analyses import (
    JobAnalysisVersion,
    JobAnalysisVersionDraft,
    create_job_analysis_version,
    get_job_analysis_versions,
)
from job_finder.jobs import JobContentVersion, get_job, get_job_content_versions, get_job_origins
from job_finder.openai_client import (
    OpenAiClientError,
    OpenAiTimeoutError,
    OpenAiUnavailableError,
    OpenAiUsage,
)
from job_finder.profile_criteria import ProfileCriteria
from job_finder.profiles import get_current_profile_version
from job_finder.secret_store import SecretStoreError
from job_finder.settings import Settings

router = APIRouter(prefix="/api", tags=["ai-analysis"])


class JobAnalysisRequest(BaseModel):
    """An explicit analysis mode; detailed reasoning is never the default."""

    model_config = ConfigDict(extra="forbid")

    mode: AnalysisMode = "batch"


class BudgetResponse(BaseModel):
    budget_usd: float | None
    spent_usd: float
    percent: float
    alerts: list[int]
    blocked: bool


class JobAnalysisResponse(BaseModel):
    """Transient validated analysis; persistence is intentionally a later concern."""

    job_id: int
    job_content_version_id: int
    analysis_id: int
    analysis_version: int
    analysis: StructuredJobAnalysis
    fit: HybridFitScore
    explanation: JobExplanation
    model: str
    prompt_version: str
    usage: AnalysisUsage
    budget: BudgetResponse


class JobAnalysisVersionResponse(BaseModel):
    """An immutable provenance-rich historical analysis returned by the local API."""

    id: int
    job_id: int
    job_content_version_id: int
    profile_version_id: int
    version_number: int
    model: str
    prompt_version: str
    analysis: StructuredJobAnalysis
    fit: HybridFitScore
    explanation: JobExplanation
    created_at: datetime
    usage: AnalysisUsage


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
    request: Request,
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

    profile = ProfileCriteria.model_validate(profile_version.criteria)
    mode = payload.mode if payload is not None else "batch"
    prompt_cache: AnalysisPromptCache = getattr(
        request.app.state,
        "analysis_prompt_cache",
        AnalysisPromptCache(),
    )
    cached_instructions = prompt_cache.get(profile_version.id, profile, mode)
    pricing = pricing_from_settings(request.app.state.settings)
    budget = _current_budget(session, request.app.state.settings)
    if budget.blocked:
        analysis = build_fallback_analysis(
            profile,
            title=job.title,
            company=job.company,
            location=job.location,
            raw_content=latest_content.raw_content,
            reason="limite mensal de custo atingido",
        )
        execution = None
        usage = usage_from_response(
            OpenAiUsage(),
            0,
            pricing=pricing,
            cache_hit=cached_instructions.hit,
            fallback=True,
            fallback_reason="limite mensal de custo atingido",
        )
        model = "deterministic-fallback"
        prompt_version = "local-fallback"
    else:
        try:
            with AI_BUDGET_LOCK:
                execution = analyze_job_content(
                    client,
                    api_key,
                    profile=profile,
                    title=job.title,
                    company=job.company,
                    location=job.location,
                    raw_content=latest_content.raw_content,
                    mode=mode,
                    instructions_override=cached_instructions.value,
                )
            analysis = execution.analysis
            usage = usage_from_response(
                execution.usage,
                execution.latency_ms,
                pricing=pricing,
                cache_hit=cached_instructions.hit,
            )
            model = execution.model
            prompt_version = execution.prompt_version
        except (OpenAiTimeoutError, OpenAiUnavailableError) as error:
            analysis = build_fallback_analysis(
                profile,
                title=job.title,
                company=job.company,
                location=job.location,
                raw_content=latest_content.raw_content,
                reason=str(error),
            )
            execution = None
            usage = usage_from_response(
                OpenAiUsage(),
                0,
                pricing=pricing,
                cache_hit=cached_instructions.hit,
                fallback=True,
                fallback_reason=str(error),
            )
            model = "deterministic-fallback"
            prompt_version = "local-fallback"
        except JobAnalysisError as error:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(error),
            ) from error
        except OpenAiClientError as error:
            raise translate_openai_error(error) from error

    fit = calculate_hybrid_fit(
        ProfileCriteria.model_validate(profile_version.criteria),
        analysis,
        description=latest_content.raw_content,
    )
    explanation = build_explanation(
        analysis,
        title=job.title,
        company=job.company,
        location=job.location,
        raw_content=latest_content.raw_content,
    )
    record = create_job_analysis_version(
        session,
        JobAnalysisVersionDraft(
            profile_version_id=profile_version.id,
            job_id=job.id,
            job_content_version_id=latest_content.id,
            model=model,
            prompt_version=prompt_version,
            analysis=analysis.model_dump(mode="json"),
            fit=fit.model_dump(mode="json"),
            explanation=explanation.model_dump(mode="json"),
            usage=usage.model_dump(mode="json"),
        ),
    )
    session.commit()
    session.refresh(record)

    return JobAnalysisResponse(
        job_id=job.id,
        job_content_version_id=latest_content.id,
        analysis_id=record.id,
        analysis_version=record.version_number,
        analysis=analysis,
        fit=fit,
        explanation=explanation,
        model=model,
        prompt_version=prompt_version,
        usage=usage,
        budget=_budget_response(_current_budget(session, request.app.state.settings)),
    )


@router.get("/jobs/{job_id}/analyses", response_model=list[JobAnalysisVersionResponse])
def list_job_analysis_history(
    job_id: int,
    session: SessionDependency,
) -> list[JobAnalysisVersionResponse]:
    """Return all immutable analyses for a known local job in generation order."""

    if get_job(session, job_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vaga não encontrada.")
    records = get_job_analysis_versions(session, job_id)
    return [_analysis_version_response(record) for record in records]


def _latest_job_content(session: Session, job_id: int) -> JobContentVersion | None:
    """Select the newest source snapshot deterministically across all job origins."""

    versions = [
        version
        for origin in get_job_origins(session, job_id)
        for version in get_job_content_versions(session, origin.id)
    ]
    return max(versions, key=lambda version: (version.captured_at, version.id), default=None)


def _analysis_version_response(record: JobAnalysisVersion) -> JobAnalysisVersionResponse:
    return JobAnalysisVersionResponse(
        id=record.id,
        job_id=record.job_id,
        job_content_version_id=record.job_content_version_id,
        profile_version_id=record.profile_version_id,
        version_number=record.version_number,
        model=record.model,
        prompt_version=record.prompt_version,
        analysis=StructuredJobAnalysis.model_validate(record.analysis),
        fit=HybridFitScore.model_validate(record.fit),
        explanation=JobExplanation.model_validate(record.explanation),
        created_at=record.created_at,
        usage=AnalysisUsage.model_validate(record.usage or {}),
    )


def _current_budget(session: Session, settings: Settings) -> BudgetState:
    from sqlalchemy import select

    config = BudgetConfig.from_settings(settings)
    if config.monthly_budget_usd is None:
        return evaluate_budget(0, config)
    from job_finder.job_analyses import JobAnalysisVersion

    now = datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    records = session.scalars(
        select(JobAnalysisVersion).where(JobAnalysisVersion.created_at >= start)
    )
    spent = 0.0
    for record in records:
        value = (record.usage or {}).get("estimated_cost_usd")
        if isinstance(value, (int, float)):
            spent += float(value)
    return evaluate_budget(spent, config)


def _budget_response(state: BudgetState) -> BudgetResponse:
    return BudgetResponse(
        budget_usd=state.budget_usd,
        spent_usd=state.spent_usd,
        percent=state.percent,
        alerts=list(state.alerts),
        blocked=state.blocked,
    )
