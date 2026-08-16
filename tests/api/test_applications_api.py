import asyncio
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


@pytest.mark.anyio
async def test_mark_job_applied_creates_application_and_is_idempotent(application) -> None:
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        job_id = await _create_job(client)
        first = await client.post(f"/api/jobs/{job_id}/application/applied")
        repeated = await client.post(f"/api/jobs/{job_id}/application/applied")

    assert first.status_code == 200
    assert repeated.status_code == 200
    assert repeated.json()["id"] == first.json()["id"]
    assert repeated.json()["current_status"] == "applied"
    assert [event["kind"] for event in repeated.json()["events"]] == [
        "initial",
        "transition",
    ]
    assert [event["to_status"] for event in repeated.json()["events"]] == ["found", "applied"]


@pytest.mark.anyio
async def test_mark_job_applied_moves_pending_application(application) -> None:
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        job_id = await _create_job(client)
        created = await client.post(f"/api/jobs/{job_id}/application")
        pending = await client.post(
            f"/api/applications/{created.json()['id']}/transition",
            json={"to_status": "pending"},
        )
        applied = await client.post(f"/api/jobs/{job_id}/application/applied")

    assert pending.status_code == 200
    assert applied.status_code == 200
    assert applied.json()["current_status"] == "applied"
    assert [event["to_status"] for event in applied.json()["events"]] == [
        "found",
        "pending",
        "applied",
    ]


@pytest.mark.anyio
async def test_mark_job_applied_does_not_regress_later_pipeline_status(application) -> None:
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        job_id = await _create_job(client)
        created = await client.post(f"/api/jobs/{job_id}/application")
        await client.post(
            f"/api/applications/{created.json()['id']}/transition",
            json={"to_status": "applied"},
        )
        interview = await client.post(
            f"/api/applications/{created.json()['id']}/transition",
            json={"to_status": "interview"},
        )
        response = await client.post(f"/api/jobs/{job_id}/application/applied")

    assert interview.status_code == 200
    assert response.status_code == 409
    assert response.json()["detail"] == "A candidatura já avançou para a fase interview."


@pytest.mark.anyio
async def test_mark_job_applied_returns_not_found_for_unknown_job(application) -> None:
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/jobs/999999/application/applied")

    assert response.status_code == 404
    assert response.json()["detail"] == "Vaga não encontrada."


@pytest.mark.anyio
async def test_mark_job_applied_is_safe_for_concurrent_requests(application) -> None:
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        job_id = await _create_job(client)
        responses = await asyncio.gather(
            client.post(f"/api/jobs/{job_id}/application/applied"),
            client.post(f"/api/jobs/{job_id}/application/applied"),
        )

    assert [response.status_code for response in responses] == [200, 200]
    assert responses[0].json()["id"] == responses[1].json()["id"]
    assert len(responses[0].json()["events"]) == 2
