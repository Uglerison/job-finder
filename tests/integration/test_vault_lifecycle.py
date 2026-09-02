from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from job_finder.main import create_app
from job_finder.settings import Settings


@pytest.mark.anyio
async def test_shutdown_clears_vault_session_and_restart_preserves_ciphertext(
    tmp_path: Path,
) -> None:
    settings = Settings(data_dir=tmp_path, environment="test")
    app = create_app(settings)
    password = "senha longa somente em memoria"
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            assert (
                await client.post("/api/vault/create", json={"vault_password": password})
            ).status_code == 200
            assert (
                await client.put("/api/search/providers/jooble", json={"api_key": "fake-key"})
            ).status_code == 200
            vault = app.state.secret_vault
            assert vault.is_unlocked()
    assert not vault.is_unlocked()
    assert vault.get_unlocked_provider_secret("jooble") is None

    restarted = create_app(settings)
    async with restarted.router.lifespan_context(restarted):
        async with AsyncClient(
            transport=ASGITransport(app=restarted), base_url="http://testserver"
        ) as client:
            assert (await client.get("/api/vault")).json() == {
                "configured": True,
                "unlocked": False,
            }
            assert (
                await client.post("/api/vault/unlock", json={"vault_password": password})
            ).json()["unlocked"]
            assert restarted.state.secret_vault.get_unlocked_provider_secret("jooble") == "fake-key"
