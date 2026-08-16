from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from job_finder.database import create_database_engine, create_session_factory, run_migrations
from job_finder.main import create_app
from job_finder.settings import Settings


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def application(tmp_path: Path):
    run_migrations(tmp_path)
    app = create_app(Settings(data_dir=tmp_path, environment="test"))
    app.state.session_factory = create_session_factory(create_database_engine(tmp_path))
    return app


@pytest.mark.anyio
async def test_preferences_api_returns_defaults_and_persists_updates(application) -> None:
    transport = ASGITransport(app=application)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        defaults_response = await client.get("/api/preferences")
        update_response = await client.put(
            "/api/preferences",
            json={
                "locale": "en-US",
                "currency": "USD",
                "timezone": "America/New_York",
                "retention_days": 90,
            },
        )
        current_response = await client.get("/api/preferences")

    assert defaults_response.status_code == 200
    assert defaults_response.json() == {
        "locale": "pt-BR",
        "currency": "BRL",
        "timezone": "America/Sao_Paulo",
        "retention_days": 365,
    }
    assert update_response.status_code == 200
    assert current_response.json() == {
        "locale": "en-US",
        "currency": "USD",
        "timezone": "America/New_York",
        "retention_days": 90,
    }
