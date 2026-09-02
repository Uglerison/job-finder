from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from job_finder.database import create_database_engine, create_session_factory, run_migrations
from job_finder.main import create_app
from job_finder.settings import Settings


@pytest.mark.anyio
async def test_global_vault_create_save_unlock_and_lock(tmp_path: Path) -> None:
    run_migrations(tmp_path)
    app = create_app(Settings(data_dir=tmp_path, environment="test"))
    app.state.session_factory = create_session_factory(create_database_engine(tmp_path))
    password = "senha unica do cofre local"
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        assert (await client.get("/api/vault")).json() == {
            "configured": False,
            "unlocked": False,
        }
        created = await client.post("/api/vault/create", json={"vault_password": password})
        assert created.status_code == 200
        assert created.json() == {"configured": True, "unlocked": True}
        saved_ai = await client.put(
            "/api/ai/api-key", json={"api_key": "sk-test-12345678901234567890"}
        )
        saved_provider = await client.put(
            "/api/search/providers/jsearch", json={"api_key": "test-key"}
        )
        assert saved_ai.status_code == saved_provider.status_code == 200
        assert (
            await client.put("/api/search/providers/jooble", json={"api_key": "jooble-key"})
        ).status_code == 200
        assert (
            await client.put(
                "/api/search/providers/adzuna", json={"app_id": "app-id", "app_key": "app-key"}
            )
        ).status_code == 200
        duplicate = await client.post(
            "/api/vault/create", json={"vault_password": "outra senha diferente"}
        )
        assert duplicate.status_code == 409
        assert (await client.post("/api/vault/lock")).json()["unlocked"] is False
        assert (await client.get("/api/ai/settings")).json()["unlocked"] is False
        assert not any(
            item["unlocked"] for item in (await client.get("/api/search/providers")).json()
        )
        blocked_save = await client.put(
            "/api/search/providers/jooble", json={"api_key": "other-key"}
        )
        assert blocked_save.status_code != 200
        wrong = await client.post(
            "/api/vault/unlock", json={"vault_password": "senha incorreta longa"}
        )
        assert wrong.status_code != 200
        assert (await client.get("/api/vault")).json()["unlocked"] is False
        unlocked = await client.post("/api/vault/unlock", json={"vault_password": password})
        assert unlocked.json()["unlocked"] is True
        assert (await client.get("/api/ai/settings")).json()["unlocked"] is True
        assert all(item["unlocked"] for item in (await client.get("/api/search/providers")).json())
        for response in (created, saved_ai, saved_provider, wrong, unlocked):
            assert password not in response.text
            assert "sk-test-12345678901234567890" not in response.text


@pytest.mark.anyio
@pytest.mark.parametrize("value", ["curta123", {"password": "never-echo-this-password"}])
async def test_vault_validation_never_echoes_password_input(tmp_path: Path, value: object) -> None:
    app = create_app(Settings(data_dir=tmp_path, environment="test"))
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.post("/api/vault/create", json={"vault_password": value})
    assert response.status_code == 422
    assert "curta123" not in response.text
    assert "never-echo-this-password" not in response.text
