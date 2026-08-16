"""Unified job-search API that keeps provider details server-side."""

import json
import logging
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, SecretStr, field_validator
from sqlalchemy.orm import Session, sessionmaker

from job_finder.aggregated_search import (
    AdzunaProvider,
    AggregatedSearchResult,
    JobProvider,
    JobSearchParams,
    JoobleProvider,
    JSearchProvider,
    LegacySourceProvider,
    SearchAggregator,
    SearchCache,
    SearchOutcome,
)
from job_finder.secret_store import EncryptedDatabaseVault, SecretStoreError
from job_finder.settings import Settings
from job_finder.source_adapters import SourceRegistry
from job_finder.source_dedup import find_exact_match, ingest_candidate
from job_finder.source_models import ensure_default_sources

router = APIRouter(prefix="/api/search", tags=["aggregated-search"])
logger = logging.getLogger(__name__)

ProviderName = Literal["jsearch", "adzuna", "jooble"]


class AggregatedJobResponse(BaseModel):
    job_id: int | None
    review_required: bool
    title: str
    company: str
    location: str | None
    description: str
    salary: str | None
    work_model: str | None
    url: str
    source: str | None
    published_at: datetime | None


class ProviderRunResponse(BaseModel):
    provider: str
    display_name: str
    status: Literal["success", "empty", "skipped", "failed"]
    duration_ms: int
    candidates: int
    fallback: bool
    error: str | None


class AggregatedSearchResponse(BaseModel):
    jobs: list[AggregatedJobResponse]
    provider_runs: list[ProviderRunResponse]
    partial: bool
    warnings: list[str]
    cache_hit: bool
    outcome: SearchOutcome
    message: str


class ProviderCredentialStatus(BaseModel):
    provider: ProviderName
    configured: bool
    unlocked: bool
    storage: Literal["encrypted_database", "environment", "not_configured"]


class ProviderCredentialRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    api_key: SecretStr | None = None
    app_id: SecretStr | None = None
    app_key: SecretStr | None = None
    vault_password: SecretStr

    @field_validator("vault_password")
    @classmethod
    def validate_password(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 12:
            raise ValueError("A senha do cofre deve ter pelo menos 12 caracteres.")
        return value


class ProviderUnlockRequest(BaseModel):
    vault_password: SecretStr

    @field_validator("vault_password")
    @classmethod
    def validate_password(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 12:
            raise ValueError("A senha do cofre deve ter pelo menos 12 caracteres.")
        return value


async def get_session(request: Request) -> AsyncIterator[Session]:
    session_factory: sessionmaker[Session] = request.app.state.session_factory
    with session_factory() as session:
        yield session


SessionDependency = Annotated[Session, Depends(get_session)]


def _app_state(request_or_application: Request | FastAPI) -> Any:
    return (
        request_or_application.app.state
        if isinstance(request_or_application, Request)
        else request_or_application.state
    )


def _vault(request_or_application: Request | FastAPI) -> EncryptedDatabaseVault:
    state = _app_state(request_or_application)
    vault = getattr(state, "secret_vault", None)
    if vault is None:
        vault = EncryptedDatabaseVault(state.session_factory)
        state.secret_vault = vault
    return vault


def _provider_status(
    request_or_application: Request | FastAPI, provider: ProviderName
) -> ProviderCredentialStatus:
    vault = _vault(request_or_application)
    settings: Settings = _app_state(request_or_application).settings
    environment_value = {
        "jsearch": settings.jsearch_api_key,
        "adzuna": settings.adzuna_app_key,
        "jooble": settings.jooble_api_key,
    }[provider]
    encrypted = vault.has_provider_secret(provider)
    return ProviderCredentialStatus(
        provider=provider,
        configured=encrypted or environment_value is not None,
        unlocked=(vault.get_unlocked_provider_secret(provider) is not None)
        or environment_value is not None,
        storage=(
            "encrypted_database"
            if encrypted
            else "environment"
            if environment_value is not None
            else "not_configured"
        ),
    )


@router.get("/providers", response_model=list[ProviderCredentialStatus])
def list_provider_credentials(request: Request) -> list[ProviderCredentialStatus]:
    """Return provider credential state without returning credential material."""

    try:
        providers: tuple[ProviderName, ...] = ("jsearch", "adzuna", "jooble")
        return [_provider_status(request, provider) for provider in providers]
    except SecretStoreError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.put("/providers/{provider}", response_model=ProviderCredentialStatus)
def save_provider_credential(
    provider: ProviderName,
    payload: ProviderCredentialRequest,
    request: Request,
) -> ProviderCredentialStatus:
    """Encrypt provider credentials in SQLite and unlock them for this process."""

    if provider == "adzuna":
        if not payload.app_id or not payload.app_key:
            raise HTTPException(status_code=422, detail="Adzuna exige app_id e app_key.")
        value = json.dumps(
            {
                "app_id": payload.app_id.get_secret_value(),
                "app_key": payload.app_key.get_secret_value(),
            },
        )
    else:
        if not payload.api_key:
            raise HTTPException(status_code=422, detail="Informe a API key do provider.")
        value = payload.api_key.get_secret_value()
    try:
        vault = _vault(request)
        vault.save_provider_secret(provider, value, payload.vault_password.get_secret_value())
        return _provider_status(request, provider)
    except SecretStoreError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error


@router.post("/providers/{provider}/unlock", response_model=ProviderCredentialStatus)
def unlock_provider_credential(
    provider: ProviderName,
    payload: ProviderUnlockRequest,
    request: Request,
) -> ProviderCredentialStatus:
    """Unlock one encrypted provider credential for the current app process."""

    try:
        vault = _vault(request)
        vault.unlock_provider_secret(provider, payload.vault_password.get_secret_value())
        return _provider_status(request, provider)
    except SecretStoreError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error


def _credential(request_or_application: Request | FastAPI, provider: str) -> str | None:
    vault = _vault(request_or_application)
    stored = vault.get_unlocked_provider_secret(provider)
    if stored is not None:
        return stored
    settings: Settings = _app_state(request_or_application).settings
    value = {
        "jsearch": settings.jsearch_api_key,
        "adzuna": settings.adzuna_app_key,
        "jooble": settings.jooble_api_key,
    }[provider]
    return value.get_secret_value() if value else None


def _providers(request_or_application: Request | FastAPI, session: Session) -> list[JobProvider]:
    configured: list[JobProvider] = []
    jsearch_key = _credential(request_or_application, "jsearch")
    configured.append(JSearchProvider(api_key=jsearch_key))
    adzuna_raw = _credential(request_or_application, "adzuna")
    settings: Settings = _app_state(request_or_application).settings
    app_id = settings.adzuna_app_id
    if adzuna_raw:
        try:
            parsed = json.loads(adzuna_raw)
            adzuna_app_id = parsed.get("app_id")
            adzuna_key = parsed.get("app_key")
        except (TypeError, ValueError):
            adzuna_app_id = app_id.get_secret_value() if app_id else None
            adzuna_key = adzuna_raw
    else:
        adzuna_app_id = app_id.get_secret_value() if app_id else None
        adzuna_key = None
    configured.append(AdzunaProvider(app_id=adzuna_app_id, app_key=adzuna_key))
    configured.append(JoobleProvider(api_key=_credential(request_or_application, "jooble")))

    registry: SourceRegistry = _app_state(request_or_application).source_registry
    for source in ensure_default_sources(session):
        if source.enabled:
            adapter = registry.get(source.source_key, source.endpoint, source.timeout_seconds)
            configured.append(LegacySourceProvider(source.source_key, source.display_name, adapter))
    return configured


def _response(
    result: AggregatedSearchResult,
    job_ids: list[int | None],
    review_required: list[bool],
) -> AggregatedSearchResponse:
    return AggregatedSearchResponse(
        jobs=[
            AggregatedJobResponse(
                job_id=job_ids[index] if index < len(job_ids) else None,
                review_required=(review_required[index] if index < len(review_required) else False),
                title=item.title,
                company=item.company,
                location=item.location,
                description=item.description,
                salary=item.salary,
                work_model=item.work_model,
                url=item.url,
                source=item.source_label,
                published_at=item.published_at,
            )
            for index, item in enumerate(result.candidates)
        ],
        provider_runs=[ProviderRunResponse(**run.__dict__) for run in result.provider_runs],
        partial=result.partial,
        warnings=list(result.warnings),
        cache_hit=result.cache_hit,
        outcome=result.outcome,
        message=result.message,
    )


@router.post("", response_model=AggregatedSearchResponse)
async def search_jobs(
    payload: JobSearchParams,
    request: Request,
    session: SessionDependency,
) -> AggregatedSearchResponse:
    """Search providers selectively, persist normalized jobs and return one result shape."""

    try:
        providers = getattr(request.app.state, "aggregated_providers", None)
        if providers is None:
            providers = _providers(request, session)
        aggregator = SearchAggregator(
            providers,
            cache=getattr(
                request.app.state,
                "aggregated_cache",
                SearchCache(request.app.state.settings.search_cache_ttl_seconds),
            ),
            minimum_results=request.app.state.settings.search_minimum_results,
        )
        request.app.state.aggregated_cache = aggregator.cache
        result = await aggregator.search(payload)
        job_ids: list[int | None] = []
        review_required: list[bool] = []
        if not result.cache_hit:
            for candidate in result.candidates:
                dedupe_result = ingest_candidate(session, candidate)
                # Approximate matches stay pending review and never point the
                # card at an existing job that may not be the same listing.
                job_ids.append(dedupe_result.job.id if dedupe_result.job is not None else None)
                review_required.append(dedupe_result.suggestion is not None)
            session.commit()
        else:
            for candidate in result.candidates:
                job, _reason = find_exact_match(session, candidate)
                job_ids.append(job.id if job is not None else None)
                review_required.append(False)
        return _response(result, job_ids, review_required)
    except HTTPException:
        raise
    except Exception as error:
        session.rollback()
        logger.exception(
            "aggregated_search request=failed error_type=%s",
            type(error).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A busca encontrou uma falha interna. Consulte o log local e tente novamente.",
        ) from error
