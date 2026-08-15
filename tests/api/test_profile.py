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


@pytest.fixture
def valid_profile_payload() -> dict[str, object]:
    return {
        "target_roles": ["Backend Engineer"],
        "skills": ["Python", "FastAPI"],
        "languages": [{"code": "en", "minimum_level": "professional"}],
        "salary_expectation": {
            "currency": "BRL",
            "minimum_monthly": 10000,
            "maximum_monthly": 15000,
        },
        "weights": {"skills": 40, "experience": 35, "location": 25},
        "restrictions": {
            "work_models": ["remote"],
            "locations": ["Brasil"],
            "excluded_keywords": [],
        },
    }


@pytest.mark.anyio
async def test_profile_api_reads_empty_creates_and_versions_updates(
    application,
    valid_profile_payload: dict[str, object],
) -> None:
    transport = ASGITransport(app=application)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        empty_response = await client.get("/api/profile")
        created_response = await client.put("/api/profile", json=valid_profile_payload)
        valid_profile_payload["restrictions"] = {
            "work_models": ["hybrid"],
            "locations": ["São Paulo"],
            "excluded_keywords": [],
        }
        updated_response = await client.put("/api/profile", json=valid_profile_payload)
        current_response = await client.get("/api/profile")

    assert empty_response.json() is None
    assert created_response.status_code == 200
    assert created_response.json()["version_number"] == 1
    assert updated_response.status_code == 200
    assert updated_response.json()["version_number"] == 2
    assert current_response.json()["criteria"]["restrictions"]["work_models"] == ["hybrid"]


@pytest.mark.anyio
async def test_profile_api_rejects_invalid_criteria(
    application,
    valid_profile_payload: dict[str, object],
) -> None:
    valid_profile_payload["weights"] = {"skills": 20}
    transport = ASGITransport(app=application)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.put("/api/profile", json=valid_profile_payload)

    assert response.status_code == 422
