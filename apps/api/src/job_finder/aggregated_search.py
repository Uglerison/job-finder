"""Provider-agnostic job search with deterministic normalization and ranking."""

import logging
import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from math import ceil
from time import monotonic
from typing import Literal, Protocol
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

from job_finder.job_import import sanitize_html, validate_public_url
from job_finder.normalization import normalize_url
from job_finder.source_adapters import (
    CancellationToken,
    SafeHttpClient,
    SourceAdapter,
    SourceAdapterError,
    SourceCandidate,
    SourceRateLimitError,
    SourceSearchRequest,
    SourceSearchResult,
)

WorkModel = Literal["remote", "hybrid", "on_site", "unknown"]
SearchOutcome = Literal[
    "results",
    "no_results",
    "partial",
    "not_configured",
    "rate_limited",
    "failed",
]

logger = logging.getLogger(__name__)


class JobSearchParams(BaseModel):
    """Bounded, provider-independent search inputs."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=2, max_length=120)
    location: str | None = Field(default=None, max_length=120)
    work_model: Literal["all", "remote", "hybrid", "on_site"] = "all"
    country: str = Field(default="br", min_length=2, max_length=2)
    language: str = Field(default="pt-BR", min_length=2, max_length=10)
    page: int = Field(default=1, ge=1, le=50)
    limit: int = Field(default=20, ge=1, le=100)

    @field_validator("query", "location")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        return cleaned or None

    @field_validator("country")
    @classmethod
    def normalize_country(cls, value: str) -> str:
        return value.strip().casefold()


@dataclass(frozen=True)
class ProviderRun:
    """Safe operational outcome for one provider attempt."""

    provider: str
    display_name: str
    status: Literal["success", "empty", "skipped", "failed"]
    duration_ms: int
    candidates: int
    fallback: bool
    error: str | None = None


@dataclass(frozen=True)
class AggregatedSearchResult:
    """Ranked candidates plus provider diagnostics safe for the local UI."""

    candidates: tuple[SourceCandidate, ...]
    provider_runs: tuple[ProviderRun, ...]
    partial: bool
    warnings: tuple[str, ...] = ()
    cache_hit: bool = False
    outcome: SearchOutcome = "no_results"
    message: str = "Nenhuma vaga encontrada."


class JobProvider(Protocol):
    """Small adapter contract used by the sequential aggregator."""

    provider_key: str
    display_name: str

    async def search(
        self,
        params: JobSearchParams,
        cancellation: CancellationToken | None = None,
    ) -> SourceSearchResult:
        """Search one provider with bounded, normalized output."""


class ProviderNotConfigured(SourceAdapterError):
    """Raised when a provider has no credential available."""


class _JsonProvider:
    provider_key = ""
    display_name = ""

    def __init__(self, endpoint: str, client: SafeHttpClient | None = None) -> None:
        self.endpoint = validate_public_url(endpoint)
        self.client = client or SafeHttpClient()

    def _require(self, value: str | None) -> str:
        if value is None or not value.strip():
            raise ProviderNotConfigured(f"{self.display_name} não está configurado.")
        return value.strip()


class JSearchProvider(_JsonProvider):
    """JSearch adapter using the RapidAPI-compatible JSON contract."""

    provider_key = "jsearch"
    display_name = "JSearch"

    def __init__(
        self,
        endpoint: str = "https://jsearch.p.rapidapi.com/search",
        api_key: str | None = None,
        client: SafeHttpClient | None = None,
    ) -> None:
        super().__init__(endpoint, client)
        self.api_key = api_key

    async def search(
        self,
        params: JobSearchParams,
        cancellation: CancellationToken | None = None,
    ) -> SourceSearchResult:
        key = self._require(self.api_key)
        parsed = urlsplit(self.endpoint)
        payload = await self.client.get_json(
            self.endpoint,
            params={
                "query": _provider_query(params),
                "page": params.page,
                "num_pages": max(1, min(3, ceil(params.limit / 10))),
                "country": params.country,
                "language": params.language,
                "date_posted": "all",
            },
            headers={
                "X-RapidAPI-Key": key,
                "X-RapidAPI-Host": parsed.hostname or "jsearch.p.rapidapi.com",
            },
            cancellation=cancellation,
        )
        items = payload.get("data", []) if isinstance(payload, dict) else []
        candidates = [
            candidate
            for item in items[: params.limit]
            if isinstance(item, dict)
            for candidate in [_jsearch_candidate(item)]
            if candidate is not None and _matches_work_model(candidate, params.work_model)
        ]
        return SourceSearchResult(tuple(candidates), partial=False)


class AdzunaProvider(_JsonProvider):
    """Adzuna adapter for the country-scoped search endpoint."""

    provider_key = "adzuna"
    display_name = "Adzuna"

    def __init__(
        self,
        endpoint: str = "https://api.adzuna.com/v1/api/jobs",
        app_id: str | None = None,
        app_key: str | None = None,
        client: SafeHttpClient | None = None,
    ) -> None:
        super().__init__(endpoint.rstrip("/"), client)
        self.app_id = app_id
        self.app_key = app_key

    async def search(
        self,
        params: JobSearchParams,
        cancellation: CancellationToken | None = None,
    ) -> SourceSearchResult:
        app_id = self._require(self.app_id)
        app_key = self._require(self.app_key)
        endpoint = f"{self.endpoint}/{params.country}/search/{params.page}"
        payload = await self.client.get_json(
            endpoint,
            params={
                "app_id": app_id,
                "app_key": app_key,
                "results_per_page": params.limit,
                "what": params.query,
                "where": params.location or "",
                "content-type": "application/json",
            },
            cancellation=cancellation,
        )
        items = payload.get("results", []) if isinstance(payload, dict) else []
        candidates = [
            candidate
            for item in items[: params.limit]
            if isinstance(item, dict)
            for candidate in [_adzuna_candidate(item)]
            if candidate is not None and _matches_work_model(candidate, params.work_model)
        ]
        return SourceSearchResult(tuple(candidates), partial=False)


class JoobleProvider(_JsonProvider):
    """Jooble adapter using its key-in-path JSON POST contract."""

    provider_key = "jooble"
    display_name = "Jooble"

    def __init__(
        self,
        endpoint: str = "https://jooble.org/api",
        api_key: str | None = None,
        client: SafeHttpClient | None = None,
    ) -> None:
        super().__init__(endpoint.rstrip("/"), client)
        self.api_key = api_key

    async def search(
        self,
        params: JobSearchParams,
        cancellation: CancellationToken | None = None,
    ) -> SourceSearchResult:
        key = self._require(self.api_key)
        payload = await self.client.post_json(
            f"{self.endpoint}/{key}",
            json_body={
                "keywords": params.query,
                "location": params.location or "Brasil",
                "page": params.page,
                "searchMode": "1",
            },
            cancellation=cancellation,
        )
        items = payload.get("jobs", []) if isinstance(payload, dict) else []
        candidates = [
            candidate
            for item in items[: params.limit]
            if isinstance(item, dict)
            for candidate in [_jooble_candidate(item)]
            if candidate is not None and _matches_work_model(candidate, params.work_model)
        ]
        return SourceSearchResult(tuple(candidates), partial=False)


class LegacySourceProvider:
    """Bridge an existing source adapter into the provider contract."""

    def __init__(self, source_key: str, display_name: str, adapter: SourceAdapter) -> None:
        self.provider_key = source_key
        self.display_name = display_name
        self.adapter = adapter

    async def search(
        self,
        params: JobSearchParams,
        cancellation: CancellationToken | None = None,
    ) -> SourceSearchResult:
        return await self.adapter.search(
            SourceSearchRequest(
                query=params.query,
                location=params.location,
                limit=params.limit,
                cancellation=cancellation,
            ),
        )


class SearchCache:
    """Small process-local TTL cache; no extra infrastructure is required."""

    def __init__(self, ttl_seconds: int = 300) -> None:
        self.ttl_seconds = max(0, ttl_seconds)
        self._items: dict[str, tuple[float, AggregatedSearchResult]] = {}

    def get(self, key: str) -> AggregatedSearchResult | None:
        item = self._items.get(key)
        if item is None:
            return None
        expires_at, result = item
        if expires_at <= monotonic():
            self._items.pop(key, None)
            return None
        return AggregatedSearchResult(
            candidates=result.candidates,
            provider_runs=result.provider_runs,
            partial=result.partial,
            warnings=result.warnings,
            cache_hit=True,
            outcome=result.outcome,
            message=result.message,
        )

    def put(self, key: str, result: AggregatedSearchResult) -> None:
        if self.ttl_seconds > 0:
            self._items[key] = (monotonic() + self.ttl_seconds, result)


class SearchAggregator:
    """Sequential provider orchestration with selective fallback."""

    def __init__(
        self,
        providers: Sequence[JobProvider],
        *,
        cache: SearchCache | None = None,
        minimum_results: int = 10,
    ) -> None:
        self.providers = tuple(providers)
        self.cache = cache or SearchCache()
        self.minimum_results = max(1, minimum_results)

    async def search(
        self,
        params: JobSearchParams,
        cancellation: CancellationToken | None = None,
    ) -> AggregatedSearchResult:
        cache_key = _cache_key(params)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        collected: list[SourceCandidate] = []
        runs: list[ProviderRun] = []
        warnings: list[str] = []
        rate_limited = 0
        failed = 0
        for index, provider in enumerate(self.providers):
            if cancellation:
                cancellation.raise_if_cancelled()
            started = monotonic()
            try:
                source_result = await provider.search(params, cancellation)
                collected.extend(source_result.candidates)
                warnings.extend(source_result.warnings)
                runs.append(
                    ProviderRun(
                        provider=provider.provider_key,
                        display_name=provider.display_name,
                        status="success" if source_result.candidates else "empty",
                        duration_ms=round((monotonic() - started) * 1000),
                        candidates=len(source_result.candidates),
                        fallback=index > 0,
                    ),
                )
                logger.info(
                    "aggregated_search provider=%s status=%s duration_ms=%d "
                    "candidates=%d fallback=%s",
                    provider.provider_key,
                    runs[-1].status,
                    runs[-1].duration_ms,
                    runs[-1].candidates,
                    runs[-1].fallback,
                )
            except ProviderNotConfigured:
                runs.append(
                    ProviderRun(
                        provider=provider.provider_key,
                        display_name=provider.display_name,
                        status="skipped",
                        duration_ms=round((monotonic() - started) * 1000),
                        candidates=0,
                        fallback=index > 0,
                    ),
                )
                logger.info(
                    "aggregated_search provider=%s status=skipped "
                    "reason=not_configured fallback=%s",
                    provider.provider_key,
                    index > 0,
                )
            except SourceRateLimitError:
                rate_limited += 1
                safe_error = "limite de consultas atingido"
                warnings.append(f"{provider.display_name}: {safe_error}")
                runs.append(
                    ProviderRun(
                        provider=provider.provider_key,
                        display_name=provider.display_name,
                        status="failed",
                        duration_ms=round((monotonic() - started) * 1000),
                        candidates=0,
                        fallback=index > 0,
                        error=safe_error,
                    ),
                )
                logger.warning(
                    "aggregated_search provider=%s status=rate_limited fallback=%s",
                    provider.provider_key,
                    index > 0,
                )
            except SourceAdapterError as error:
                failed += 1
                safe_error = str(error)
                warnings.append(f"{provider.display_name}: {safe_error}")
                runs.append(
                    ProviderRun(
                        provider=provider.provider_key,
                        display_name=provider.display_name,
                        status="failed",
                        duration_ms=round((monotonic() - started) * 1000),
                        candidates=0,
                        fallback=index > 0,
                        error=safe_error,
                    ),
                )
                logger.warning(
                    "aggregated_search provider=%s status=failed fallback=%s error=%s",
                    provider.provider_key,
                    index > 0,
                    safe_error,
                )
            if len(deduplicate_candidates(collected)) >= min(params.limit, self.minimum_results):
                break

        ranked = rank_candidates(deduplicate_candidates(collected), params)
        outcome, message = _search_outcome(
            len(ranked),
            runs,
            rate_limited=rate_limited,
            failed=failed,
        )
        result = AggregatedSearchResult(
            candidates=tuple(ranked[: params.limit]),
            provider_runs=tuple(runs),
            partial=outcome == "partial",
            warnings=tuple(warnings[:5]),
            outcome=outcome,
            message=message,
        )
        self.cache.put(cache_key, result)
        return result


def deduplicate_candidates(candidates: Iterable[SourceCandidate]) -> list[SourceCandidate]:
    """Merge exact and conservative approximate duplicates in stable order."""

    selected: list[SourceCandidate] = []
    for candidate in candidates:
        duplicate_index = next(
            (
                index
                for index, existing in enumerate(selected)
                if _is_duplicate(existing, candidate)
            ),
            None,
        )
        if duplicate_index is None:
            selected.append(candidate)
        else:
            selected[duplicate_index] = _merge_candidate(
                selected[duplicate_index],
                candidate,
            )
    return selected


def rank_candidates(
    candidates: Iterable[SourceCandidate],
    params: JobSearchParams,
) -> list[SourceCandidate]:
    """Rank by query, location, modality, recency and completeness."""

    terms = {_fold(token) for token in params.query.split() if token}
    location_term = _fold(params.location or "")

    def score(candidate: SourceCandidate) -> tuple[float, str]:
        text = _fold(f"{candidate.title} {candidate.company} {candidate.description}")
        query_hits = sum(1 for term in terms if term in text)
        location_hit = int(bool(location_term and location_term in _fold(candidate.location or "")))
        mode_hit = int(params.work_model == "all" or candidate.work_model == params.work_model)
        recency = _recency_score(candidate.published_at)
        completeness = sum(
            bool(value)
            for value in (
                candidate.location,
                candidate.description,
                candidate.salary,
                candidate.work_model,
            )
        )
        total = query_hits * 10 + location_hit * 8 + mode_hit * 5 + recency * 3 + completeness
        tie_breaker = _fold(f"{candidate.title}|{candidate.company}|{candidate.url}")
        return total, tie_breaker

    return sorted(candidates, key=lambda candidate: score(candidate), reverse=True)


def _jsearch_candidate(item: dict[str, object]) -> SourceCandidate | None:
    return _candidate_from_fields(
        source_key="jsearch",
        source_label=_string(item.get("job_publisher")) or "Portal parceiro",
        external_id=_string(item.get("job_id")),
        url=_string(item.get("job_apply_link")) or _string(item.get("job_google_link")),
        title=_string(item.get("job_title")),
        company=_string(item.get("employer_name")),
        location=_join_location(
            item.get("job_city"),
            item.get("job_state"),
            item.get("job_country"),
        ),
        description=_string(item.get("job_description")),
        published_at=item.get("job_posted_at_datetime_utc"),
        work_model="remote" if item.get("job_is_remote") is True else _infer_work_model(item),
        salary=_salary(
            item.get("job_min_salary"),
            item.get("job_max_salary"),
            item.get("job_salary_currency"),
        ),
        raw_payload=item,
    )


def _adzuna_candidate(item: dict[str, object]) -> SourceCandidate | None:
    company = item.get("company")
    location = item.get("location")
    company_name = company.get("display_name") if isinstance(company, dict) else company
    location_name = location.get("display_name") if isinstance(location, dict) else location
    return _candidate_from_fields(
        source_key="adzuna",
        source_label="Portal parceiro",
        external_id=_string(item.get("id")),
        url=_string(item.get("redirect_url")),
        title=_string(item.get("title")),
        company=_string(company_name),
        location=_string(location_name),
        description=_string(item.get("description")),
        published_at=item.get("created"),
        work_model=_infer_work_model(item),
        salary=_salary(item.get("salary_min"), item.get("salary_max"), None),
        raw_payload=item,
    )


def _jooble_candidate(item: dict[str, object]) -> SourceCandidate | None:
    return _candidate_from_fields(
        source_key="jooble",
        source_label=_string(item.get("source")) or "Jooble",
        external_id=_string(item.get("id")),
        url=_string(item.get("link")),
        title=_string(item.get("title")),
        company=_string(item.get("company")),
        location=_string(item.get("location")),
        description=_string(item.get("snippet")) or _string(item.get("description")),
        published_at=item.get("updated"),
        work_model=_infer_work_model(item),
        salary=_string(item.get("salary")),
        raw_payload=item,
    )


def _candidate_from_fields(
    *,
    source_key: str,
    source_label: str,
    external_id: str | None,
    url: str | None,
    title: str | None,
    company: str | None,
    location: str | None,
    description: str | None,
    published_at: object,
    work_model: str | None,
    salary: str | None,
    raw_payload: dict[str, object],
) -> SourceCandidate | None:
    if not url or not title or not company:
        return None
    try:
        return SourceCandidate(
            source_key=source_key,
            external_id=external_id,
            url=normalize_url(url) or validate_public_url(url),
            title=" ".join(title.split()),
            company=" ".join(company.split()),
            location=" ".join(location.split()) if location else None,
            description=sanitize_html(description or title),
            published_at=_parse_timestamp(published_at),
            raw_payload=raw_payload,
            work_model=(work_model if work_model in {"remote", "hybrid", "on_site"} else "unknown"),
            salary=salary,
            source_label=source_label,
        )
    except (TypeError, ValueError):
        return None


def _provider_query(params: JobSearchParams) -> str:
    return " ".join(part for part in (params.query, params.location) if part)


def _cache_key(params: JobSearchParams) -> str:
    return "|".join(
        (
            params.query.casefold(),
            (params.location or "").casefold(),
            params.work_model,
            params.country,
            params.language,
            str(params.page),
            str(params.limit),
        ),
    )


def _search_outcome(
    result_count: int,
    runs: Sequence[ProviderRun],
    *,
    rate_limited: int,
    failed: int,
) -> tuple[SearchOutcome, str]:
    """Translate provider runs into a user-facing, actionable outcome."""

    if result_count:
        label = "vaga" if result_count == 1 else "vagas"
        if failed or rate_limited:
            return (
                "partial",
                f"Encontramos {result_count} {label}, mas algumas fontes não responderam.",
            )
        return "results", f"Encontramos {result_count} {label} para estes filtros."
    if not runs or all(run.status == "skipped" for run in runs):
        return (
            "not_configured",
            "Nenhum provider está configurado. Cadastre uma credencial na seção "
            "técnica para buscar vagas.",
        )
    if rate_limited and not any(run.status in {"success", "empty"} for run in runs):
        return (
            "rate_limited",
            "As fontes atingiram o limite de consultas. Aguarde e tente novamente.",
        )
    if failed and not any(run.status in {"success", "empty"} for run in runs):
        return (
            "failed",
            "As fontes não responderam. Verifique credenciais ou conexão e tente novamente.",
        )
    if failed or rate_limited:
        return (
            "partial",
            "Nenhuma vaga foi encontrada e algumas fontes não responderam.",
        )
    return "no_results", "Nenhuma vaga encontrada para estes filtros."


def _is_duplicate(left: SourceCandidate, right: SourceCandidate) -> bool:
    if left.url == right.url:
        return True
    title = SequenceMatcher(None, _fold(left.title), _fold(right.title)).ratio()
    company = SequenceMatcher(None, _fold(left.company), _fold(right.company)).ratio()
    location = SequenceMatcher(
        None,
        _fold(left.location or ""),
        _fold(right.location or ""),
    ).ratio()
    return (
        title >= 0.9
        and company >= 0.9
        and (location >= 0.75 or not left.location or not right.location)
    )


def _merge_candidate(left: SourceCandidate, right: SourceCandidate) -> SourceCandidate:
    labels = [value for value in (left.source_label, right.source_label) if value]
    unique_labels = list(dict.fromkeys(labels))
    raw_payload = dict(left.raw_payload)
    raw_payload["sources"] = list(dict.fromkeys([left.source_key, right.source_key]))
    return SourceCandidate(
        source_key=left.source_key,
        external_id=left.external_id or right.external_id,
        url=left.url,
        title=left.title,
        company=left.company,
        location=left.location or right.location,
        description=(
            left.description
            if len(left.description) >= len(right.description)
            else right.description
        ),
        published_at=left.published_at or right.published_at,
        expires_at=left.expires_at or right.expires_at,
        raw_payload=raw_payload,
        work_model=left.work_model if left.work_model != "unknown" else right.work_model,
        salary=left.salary or right.salary,
        source_label=" / ".join(unique_labels) if unique_labels else None,
    )


def _fold(value: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFKD", value.casefold())
        if not unicodedata.combining(character)
    )


def _matches_work_model(candidate: SourceCandidate, requested: str) -> bool:
    return requested == "all" or candidate.work_model in {requested, "unknown"}


def _infer_work_model(item: dict[str, object]) -> str:
    values = " ".join(
        str(item.get(key, ""))
        for key in (
            "job_description",
            "description",
            "snippet",
            "location",
            "type",
            "contract_type",
        )
    ).casefold()
    if "hybrid" in values:
        return "hybrid"
    if any(token in values for token in ("remote", "remoto", "home office", "work from home")):
        return "remote"
    if any(token in values for token in ("on-site", "on site", "onsite", "presencial")):
        return "on_site"
    return "unknown"


def _join_location(*values: object) -> str | None:
    parts = [_string(value) for value in values]
    joined = ", ".join(part for part in parts if part)
    return joined or None


def _salary(minimum: object, maximum: object, currency: object) -> str | None:
    if minimum is None and maximum is None:
        return None
    suffix = f" {currency}" if currency else ""
    if minimum is not None and maximum is not None:
        return f"{minimum}–{maximum}{suffix}"
    return f"{minimum or maximum}{suffix}"


def _string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_timestamp(value: object) -> datetime | None:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _recency_score(value: datetime | None) -> float:
    if value is None:
        return 0.0
    age_days = max(
        0.0,
        (datetime.now(timezone.utc) - value.astimezone(timezone.utc)).total_seconds() / 86400,
    )
    return max(0.0, 1.0 - min(age_days, 30.0) / 30.0)
