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


async def _create_job(client: AsyncClient) -> int:
    response = await client.post(
        "/api/jobs",
        json={
            "canonical_url": "https://jobs.example.com/application-api",
            "company": "Example Labs",
            "raw_content": "Descrição",
            "title": "Backend Engineer",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.anyio
async def test_application_api_creates_transitions_and_lists_history(application) -> None:
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        job_id = await _create_job(client)
        created = await client.post(f"/api/jobs/{job_id}/application")
        duplicate = await client.post(f"/api/jobs/{job_id}/application")
        moved = await client.post(
            f"/api/applications/{created.json()['id']}/transition",
            json={"to_status": "applied", "note": "Candidatura enviada"},
        )
        corrected = await client.post(
            f"/api/applications/{created.json()['id']}/transition",
            json={"to_status": "pending", "correction": True, "note": "Revisar"},
        )
        history = await client.get(f"/api/applications/{created.json()['id']}")

    assert created.status_code == 201
    assert created.json()["current_status"] == "found"
    assert duplicate.status_code == 409
    assert moved.status_code == 200
    assert moved.json()["current_status"] == "applied"
    assert corrected.status_code == 200
    assert corrected.json()["current_status"] == "pending"
    assert [event["kind"] for event in history.json()["events"]] == [
        "initial",
        "transition",
        "correction",
    ]


@pytest.mark.anyio
async def test_application_api_rejects_invalid_transition(application) -> None:
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        job_id = await _create_job(client)
        created = await client.post(f"/api/jobs/{job_id}/application")
        response = await client.post(
            f"/api/applications/{created.json()['id']}/transition",
            json={"to_status": "hired"},
        )

    assert response.status_code == 409


@pytest.mark.anyio
async def test_application_api_requires_and_persists_closure_reason(application) -> None:
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        job_id = await _create_job(client)
        created = await client.post(f"/api/jobs/{job_id}/application")
        missing_reason = await client.post(
            f"/api/applications/{created.json()['id']}/transition",
            json={"to_status": "rejected"},
        )
        closed = await client.post(
            f"/api/applications/{created.json()['id']}/transition",
            json={"to_status": "rejected", "closure_reason": "not_fit"},
        )

    assert missing_reason.status_code == 409
    assert closed.status_code == 200
    assert closed.json()["closing_reason"] == "not_fit"
    assert closed.json()["events"][-1]["closure_reason"] == "not_fit"
