import logging
from datetime import datetime, timezone
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from job_finder.database import create_database_engine, create_session_factory, run_migrations
from job_finder.main import create_app
from job_finder.settings import Settings
from job_finder.source_adapters import SourceCandidate, SourceSearchResult


@pytest.fixture
def application(tmp_path: Path):
    run_migrations(tmp_path)
    app = create_app(Settings(data_dir=tmp_path, environment="test"))
    app.state.session_factory = create_session_factory(create_database_engine(tmp_path))
    return app


class FakeProvider:
    provider_key = "fake"
    display_name = "Fonte pública"

    async def search(self, params, cancellation=None):
        return SourceSearchResult(
            (
                SourceCandidate(
                    source_key="fake",
                    external_id="fake-1",
                    url="https://jobs.example/fake-1",
                    title="Analista de Dados",
                    company="Dados Brasil",
                    location="Curitiba, PR",
                    description="Python e SQL",
                    published_at=datetime.now(timezone.utc),
                    work_model="hybrid",
                    salary="R$ 7.000",
                    source_label="Portal parceiro",
                ),
            ),
        )


@pytest.mark.anyio
async def test_unified_search_returns_normalized_jobs_without_provider_names(application) -> None:
    application.state.aggregated_providers = [FakeProvider()]
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/search",
            json={"query": "Analista de Dados", "location": "Curitiba, PR", "limit": 5},
        )

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload["jobs"][0]["job_id"], int)
    assert payload["jobs"][0]["review_required"] is False
    assert payload["jobs"][0]["title"] == "Analista de Dados"
    assert payload["jobs"][0]["source"] == "Portal parceiro"
    assert payload["provider_runs"][0]["display_name"] == "Fonte pública"
    assert payload["outcome"] == "results"
    assert payload["message"] == "Encontramos 1 vaga para estes filtros."


@pytest.mark.anyio
async def test_provider_status_never_returns_secret_material(application) -> None:
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/search/providers")

    assert response.status_code == 200
    assert all("api_key" not in item and "secret" not in item for item in response.json())


@pytest.mark.anyio
async def test_unified_search_explains_when_no_provider_returns_a_job(application) -> None:
    class EmptyProvider:
        provider_key = "empty"
        display_name = "Fonte vazia"

        async def search(self, params, cancellation=None):
            return SourceSearchResult(())

    application.state.aggregated_providers = [EmptyProvider()]
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/search",
            json={"query": "Cargo inexistente", "limit": 5},
        )

    assert response.status_code == 200
    assert response.json()["outcome"] == "no_results"
    assert response.json()["message"] == "Nenhuma vaga encontrada para estes filtros."


@pytest.mark.anyio
async def test_unified_search_logs_and_explains_an_unexpected_internal_failure(
    application,
    caplog,
    monkeypatch,
) -> None:
    application.state.aggregated_providers = [FakeProvider()]

    def fail_to_persist(*_args, **_kwargs) -> None:
        raise RuntimeError("database write failed")

    monkeypatch.setattr("job_finder.aggregated_search_api.ingest_candidate", fail_to_persist)
    transport = ASGITransport(app=application)
    with caplog.at_level(logging.ERROR, logger="job_finder.aggregated_search_api"):
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/api/search",
                json={"query": "Analista de Dados", "limit": 5},
            )

    assert response.status_code == 500
    assert response.json() == {
        "detail": "A busca encontrou uma falha interna. Consulte o log local e tente novamente."
    }
    assert "aggregated_search request=failed error_type=RuntimeError" in caplog.text


@pytest.mark.anyio
async def test_provider_credential_is_encrypted_and_can_be_unlocked(application) -> None:
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        saved = await client.put(
            "/api/search/providers/jsearch",
            json={"api_key": "jsearch-local-key", "vault_password": "senha local com doze"},
        )
        locked = await client.post(
            "/api/search/providers/jsearch/unlock",
            json={"vault_password": "senha local com doze"},
        )

    assert saved.status_code == 200
    assert saved.json() == {
        "provider": "jsearch",
        "configured": True,
        "unlocked": True,
        "storage": "encrypted_database",
    }
    assert locked.status_code == 200
    assert "jsearch-local-key" not in saved.text


@pytest.mark.anyio
async def test_one_vault_password_unlocks_all_configured_providers(application) -> None:
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        await client.put(
            "/api/search/providers/jsearch",
            json={"api_key": "jsearch-local-key", "vault_password": "senha local com doze"},
        )
        await client.put(
            "/api/search/providers/jooble",
            json={"api_key": "jooble-local-key", "vault_password": "senha local com doze"},
        )
        application.state.secret_vault.lock()
        unlocked = await client.post(
            "/api/search/providers/unlock-all",
            json={"vault_password": "senha local com doze"},
        )

    assert unlocked.status_code == 200
    payload = {item["provider"]: item for item in unlocked.json()}
    assert payload["jsearch"]["unlocked"] is True
    assert payload["jooble"]["unlocked"] is True
    assert all("api_key" not in item and "secret" not in item for item in unlocked.json())
