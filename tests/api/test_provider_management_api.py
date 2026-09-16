from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from job_finder.database import create_database_engine, create_session_factory, run_migrations
from job_finder.main import create_app
from job_finder.settings import Settings
from job_finder.source_adapters import SourceRateLimitError, SourceSearchResult


@pytest.fixture
def application(tmp_path: Path):
    run_migrations(tmp_path)
    app = create_app(Settings(data_dir=tmp_path, environment="test"))
    app.state.session_factory = create_session_factory(create_database_engine(tmp_path))
    return app


async def configure(client):
    response = await client.post(
        "/api/vault/create", json={"vault_password": "senha local de teste"}
    )
    assert response.status_code == 200
    response = await client.put("/api/search/providers/jsearch", json={"api_key": "test-secret"})
    assert response.status_code == 200


@pytest.mark.anyio
async def test_remove_provider_requires_unlock_and_keeps_other_credentials(application):
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://testserver"
    ) as c:
        await configure(c)
        await c.put("/api/search/providers/jooble", json={"api_key": "another-secret"})
        await c.post("/api/vault/lock")
        assert (await c.delete("/api/search/providers/jsearch")).status_code == 423
        await c.post("/api/vault/unlock", json={"vault_password": "senha local de teste"})
        response = await c.delete("/api/search/providers/jsearch")
        assert response.status_code == 200
        assert response.json()["configured"] is False
        statuses = (await c.get("/api/search/providers")).json()
        assert next(item for item in statuses if item["provider"] == "jooble")["configured"]
        assert "secret" not in response.text


@pytest.mark.anyio
async def test_environment_credential_cannot_be_deleted(application):
    application.state.settings.jsearch_api_key = SecretStr("environment-secret")
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://testserver"
    ) as c:
        assert (await c.delete("/api/search/providers/jsearch")).status_code == 409


@pytest.mark.anyio
async def test_test_connection_requires_configured_unlocked_provider(application):
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://testserver"
    ) as c:
        assert (await c.post("/api/search/providers/jsearch/test")).status_code == 409
        await configure(c)
        await c.post("/api/vault/lock")
        assert (await c.post("/api/search/providers/jsearch/test")).status_code == 423


@pytest.mark.anyio
async def test_connection_queries_only_selected_provider_and_does_not_persist_jobs(
    application, monkeypatch
):
    calls = []

    class Provider:
        provider_key = "jsearch"

        async def search(self, params):
            calls.append(params.limit)
            return SourceSearchResult(())

    monkeypatch.setattr("job_finder.aggregated_search_api._providers", lambda *_: [Provider()])
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://testserver"
    ) as c:
        await configure(c)
        response = await c.post("/api/search/providers/jsearch/test")
        assert response.status_code == 200
        assert response.json()["status"] == "connected"
        assert calls == [1]
        assert (await c.get("/api/jobs")).json()["items"] == []
        assert "test-secret" not in response.text


@pytest.mark.anyio
@pytest.mark.parametrize(
    "failure,code", [(SourceRateLimitError("test-secret"), 429), (RuntimeError("test-secret"), 502)]
)
async def test_connection_failure_is_safe(application, monkeypatch, failure, code):
    class Provider:
        provider_key = "jsearch"

        async def search(self, params):
            raise failure

    monkeypatch.setattr("job_finder.aggregated_search_api._providers", lambda *_: [Provider()])
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://testserver"
    ) as c:
        await configure(c)
        response = await c.post("/api/search/providers/jsearch/test")
        assert response.status_code == code
        assert "test-secret" not in response.text
