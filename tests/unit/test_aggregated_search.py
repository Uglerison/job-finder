import logging
from datetime import datetime, timezone

import httpx
import pytest
from pydantic import ValidationError

from job_finder.aggregated_search import (
    AdzunaProvider,
    JobSearchParams,
    JoobleProvider,
    JSearchProvider,
    ProviderNotConfigured,
    ProviderResponseFormatError,
    SearchAggregator,
    SearchCache,
    deduplicate_candidates,
)
from job_finder.source_adapters import (
    SafeHttpClient,
    SourceAdapterError,
    SourceCandidate,
    SourceHttpError,
    SourceRateLimitError,
    SourceSearchResult,
)


def candidate(
    *,
    source_key: str = "test",
    url: str = "https://jobs.example/1",
    title: str = "Analista de Dados",
    company: str = "Dados Brasil",
    location: str | None = "Curitiba, PR",
    work_model: str | None = "hybrid",
) -> SourceCandidate:
    return SourceCandidate(
        source_key=source_key,
        external_id=url.rsplit("/", 1)[-1],
        url=url,
        title=title,
        company=company,
        location=location,
        description="Python, SQL e análise de dados",
        published_at=datetime.now(timezone.utc),
        work_model=work_model,
        source_label=source_key.title(),
    )


def test_search_params_are_bounded_and_normalized() -> None:
    params = JobSearchParams(query="  Analista   de Dados ", location=" Curitiba, PR ")
    assert params.query == "Analista de Dados"
    assert params.location == "Curitiba, PR"
    assert params.country == "br"
    with pytest.raises(ValidationError):
        JobSearchParams(query="a")


@pytest.mark.anyio
async def test_jsearch_maps_brazilian_payload_and_headers() -> None:
    seen: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "job_id": "j-1",
                        "job_apply_link": "https://jobs.example/j-1",
                        "job_title": "Analista de Dados",
                        "employer_name": "Dados Brasil",
                        "job_city": "Curitiba",
                        "job_state": "PR",
                        "job_country": "BR",
                        "job_description": "<p>Python</p>",
                        "job_is_remote": False,
                        "job_posted_at_datetime_utc": "2026-08-15T10:00:00Z",
                        "job_min_salary": 5000,
                        "job_max_salary": 7000,
                        "job_salary_currency": "BRL",
                    },
                ],
            },
        )

    provider = JSearchProvider(
        api_key="secret",
        client=SafeHttpClient(transport=httpx.MockTransport(handler), jitter=lambda: 0.0),
    )
    result = await provider.search(
        JobSearchParams(query="Analista de Dados", location="Curitiba, PR"),
    )
    assert result.candidates[0].company == "Dados Brasil"
    assert result.candidates[0].location == "Curitiba, PR, BR"
    assert result.candidates[0].salary == "5000–7000 BRL"
    assert seen[0].headers["X-RapidAPI-Key"] == "secret"
    assert str(seen[0].url).split("?", 1)[0] == "https://jsearch.p.rapidapi.com/search-v2"
    assert dict(seen[0].url.params)["query"] == "Analista de Dados em Curitiba, PR"
    assert dict(seen[0].url.params)["num_pages"] == "1"
    assert dict(seen[0].url.params)["country"] == "br"
    assert dict(seen[0].url.params)["language"] == "pt"


@pytest.mark.anyio
async def test_jsearch_accepts_a_nested_jobs_list() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "data": {
                    "jobs": [
                        {
                            "job_id": "j-2",
                            "job_apply_link": "https://jobs.example/j-2",
                            "job_title": "Analista de Dados",
                            "employer_name": "Dados Brasil",
                            "job_description": "Python e SQL",
                        },
                    ],
                },
            },
        )

    provider = JSearchProvider(
        api_key="secret",
        client=SafeHttpClient(transport=httpx.MockTransport(handler), jitter=lambda: 0.0),
    )

    result = await provider.search(JobSearchParams(query="Analista de Dados"))

    assert [candidate.external_id for candidate in result.candidates] == ["j-2"]


@pytest.mark.anyio
async def test_jsearch_reports_an_invalid_object_payload_without_crashing_search() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {"notice": "format changed"}})

    provider = JSearchProvider(
        api_key="secret",
        client=SafeHttpClient(transport=httpx.MockTransport(handler), jitter=lambda: 0.0),
    )

    with pytest.raises(ProviderResponseFormatError, match="sem lista de vagas"):
        await provider.search(JobSearchParams(query="Analista de Dados"))


def test_jsearch_endpoint_is_canonical_and_rejects_unknown_paths() -> None:
    assert (
        JSearchProvider(endpoint="https://jsearch.p.rapidapi.com/").endpoint
        == "https://jsearch.p.rapidapi.com/search-v2"
    )
    assert (
        JSearchProvider(endpoint="https://jsearch.p.rapidapi.com/search/").endpoint
        == "https://jsearch.p.rapidapi.com/search-v2"
    )
    assert (
        JSearchProvider(endpoint="https://jsearch.p.rapidapi.com/search-v2/").endpoint
        == "https://jsearch.p.rapidapi.com/search-v2"
    )
    with pytest.raises(ValueError, match="exatamente para /search-v2"):
        JSearchProvider(endpoint="https://jsearch.p.rapidapi.com/search/search")


@pytest.mark.anyio
@pytest.mark.parametrize("status_code", [401, 403, 404])
async def test_http_error_keeps_safe_diagnostics_without_secrets(status_code: int) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code,
            json={"message": "not found", "api_key": "super-secret"},
        )

    client = SafeHttpClient(transport=httpx.MockTransport(handler), jitter=lambda: 0.0)
    with pytest.raises(SourceHttpError) as error:
        await client.get_json(
            "https://jsearch.p.rapidapi.com/search",
            params={"query": "Python"},
            headers={"X-RapidAPI-Key": "super-secret"},
            max_attempts=1,
        )
    assert error.value.status_code == status_code
    assert error.value.method == "GET"
    assert error.value.url == "https://jsearch.p.rapidapi.com/search?query=Python"
    assert "not found" in error.value.response_excerpt
    assert "super-secret" not in error.value.response_excerpt


@pytest.mark.anyio
async def test_aggregator_logs_http_diagnostics_and_continues_with_fallback(caplog) -> None:
    class HttpFailingProvider:
        provider_key = "jsearch"
        display_name = "JSearch"

        async def search(self, params, cancellation=None):
            raise SourceHttpError(
                "a fonte respondeu com HTTP 404",
                method="GET",
                url="https://jsearch.p.rapidapi.com/search?query=Python",
                status_code=404,
                duration_ms=687,
                response_excerpt='{"message":"resource not found"}',
            )

    class BackupProvider:
        provider_key = "backup"
        display_name = "Complementar"

        async def search(self, params, cancellation=None):
            return SourceSearchResult((candidate(source_key="backup"),))

    with caplog.at_level(logging.WARNING, logger="job_finder.aggregated_search"):
        result = await SearchAggregator([HttpFailingProvider(), BackupProvider()]).search(
            JobSearchParams(query="Python", limit=1),
        )

    assert result.outcome == "partial"
    assert result.candidates[0].source_key == "backup"
    assert "method=GET" in caplog.text
    assert "http_status=404" in caplog.text
    assert "request_duration_ms=687" in caplog.text


@pytest.mark.anyio
async def test_adzuna_maps_results_and_jooble_uses_post() -> None:
    methods: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        methods.append(request.method)
        if request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "id": "a-1",
                            "redirect_url": "https://jobs.example/a-1",
                            "title": "Desenvolvedor Python",
                            "company": {"display_name": "Tech BR"},
                            "location": {"display_name": "São Paulo"},
                            "description": "API Python",
                            "created": "2026-08-15T10:00:00Z",
                        },
                    ],
                },
            )
        return httpx.Response(
            200,
            json={
                "jobs": [
                    {
                        "id": "j-2",
                        "link": "https://jobs.example/j-2",
                        "title": "Desenvolvedor Python",
                        "company": "Tech BR",
                        "location": "São Paulo",
                        "snippet": "API Python",
                    },
                ],
            },
        )

    client = SafeHttpClient(transport=httpx.MockTransport(handler), jitter=lambda: 0.0)
    params = JobSearchParams(query="Desenvolvedor Python", location="São Paulo")
    adzuna = await AdzunaProvider(app_id="id", app_key="key", client=client).search(params)
    jooble = await JoobleProvider(api_key="key", client=client).search(params)
    assert adzuna.candidates[0].source_key == "adzuna"
    assert jooble.candidates[0].source_key == "jooble"
    assert methods == ["GET", "POST"]


@pytest.mark.anyio
async def test_aggregator_falls_back_only_when_needed_and_caches() -> None:
    class FailingProvider:
        provider_key = "primary"
        display_name = "Principal"

        async def search(self, params, cancellation=None):
            raise SourceAdapterError("indisponível")

    class BackupProvider:
        provider_key = "backup"
        display_name = "Complementar"
        calls = 0

        async def search(self, params, cancellation=None):
            self.calls += 1
            return SourceSearchResult(
                tuple(
                    candidate(source_key="backup", url=f"https://jobs.example/{i}")
                    for i in range(2)
                ),
            )

    backup = BackupProvider()
    aggregator = SearchAggregator(
        [FailingProvider(), backup],
        cache=SearchCache(ttl_seconds=60),
        minimum_results=10,
    )
    params = JobSearchParams(query="Analista de Dados", limit=2)
    first = await aggregator.search(params)
    second = await aggregator.search(params)
    assert first.partial is True
    assert first.candidates[0].source_key == "backup"
    assert second.cache_hit is True
    assert backup.calls == 1


@pytest.mark.anyio
async def test_aggregator_explains_empty_search_and_configuration_state() -> None:
    class EmptyProvider:
        provider_key = "empty"
        display_name = "Fonte vazia"

        async def search(self, params, cancellation=None):
            return SourceSearchResult(())

    result = await SearchAggregator([EmptyProvider()]).search(
        JobSearchParams(query="Cargo inexistente", limit=5),
    )
    assert result.outcome == "no_results"
    assert result.message == "Nenhuma vaga encontrada para estes filtros."
    assert result.partial is False


@pytest.mark.anyio
async def test_aggregator_distinguishes_rate_limit_from_no_results() -> None:
    class LimitedProvider:
        provider_key = "limited"
        display_name = "Fonte limitada"

        async def search(self, params, cancellation=None):
            raise SourceRateLimitError("limite", retry_after=60)

    result = await SearchAggregator([LimitedProvider()]).search(
        JobSearchParams(query="Python"),
    )
    assert result.outcome == "rate_limited"
    assert "limite de consultas" in result.message
    assert result.provider_runs[0].error == "limite de consultas atingido"


def test_deduplication_merges_source_metadata() -> None:
    merged = deduplicate_candidates(
        [
            candidate(source_key="jsearch", url="https://jobs.example/shared"),
            candidate(source_key="adzuna", url="https://jobs.example/shared", work_model="unknown"),
        ],
    )
    assert len(merged) == 1
    assert merged[0].source_label == "Jsearch / Adzuna"


@pytest.mark.anyio
async def test_provider_without_credential_is_safe() -> None:
    with pytest.raises(ProviderNotConfigured):
        await JSearchProvider().search(JobSearchParams(query="Python"))
