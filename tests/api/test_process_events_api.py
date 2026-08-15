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


async def _create_application(client: AsyncClient) -> int:
    job = await client.post(
        "/api/jobs",
        json={
            "canonical_url": "https://jobs.example.com/event-api",
            "company": "Example Labs",
            "raw_content": "Descrição",
            "title": "Backend Engineer",
        },
    )
    created = await client.post(f"/api/jobs/{job.json()['id']}/application")
    assert created.status_code == 201
    return created.json()["id"]


@pytest.mark.anyio
async def test_process_events_api_lists_event_and_rejects_conflict(application) -> None:
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        application_id = await _create_application(client)
        payload = {
            "kind": "interview",
            "title": "Entrevista técnica",
            "starts_at": "2026-08-15T10:00:00-03:00",
            "ends_at": "2026-08-15T11:00:00-03:00",
            "participants": ["ana@example.com"],
            "link": "https://meet.example.com/room",
            "notes": "Levar exemplos de API",
        }
        created = await client.post(f"/api/applications/{application_id}/events", json=payload)
        listed = await client.get(f"/api/applications/{application_id}/events")
        conflict = await client.post(
            f"/api/applications/{application_id}/events",
            json={
                **payload,
                "kind": "challenge",
                "title": "Desafio",
                "starts_at": "2026-08-15T10:30:00-03:00",
                "ends_at": "2026-08-15T12:00:00-03:00",
            },
        )

    assert created.status_code == 201
    assert created.json()["kind"] == "interview"
    assert created.json()["participants"] == ["ana@example.com"]
    assert listed.status_code == 200
    assert [item["title"] for item in listed.json()] == ["Entrevista técnica"]
    assert conflict.status_code == 409


@pytest.mark.anyio
async def test_process_events_api_rejects_naive_datetime(application) -> None:
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        application_id = await _create_application(client)
        response = await client.post(
            f"/api/applications/{application_id}/events",
            json={
                "kind": "deadline",
                "title": "Prazo do desafio",
                "starts_at": "2026-08-15T10:00:00",
            },
        )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_agenda_api_filters_events_by_period_and_status(application) -> None:
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        application_id = await _create_application(client)
        await client.post(
            f"/api/applications/{application_id}/events",
            json={
                "kind": "interview",
                "title": "Entrevista no período",
                "starts_at": "2026-08-15T10:00:00-03:00",
                "ends_at": "2026-08-15T11:00:00-03:00",
            },
        )
        await client.post(
            f"/api/applications/{application_id}/events",
            json={
                "kind": "deadline",
                "title": "Prazo futuro",
                "starts_at": "2026-09-15T10:00:00-03:00",
            },
        )
        filtered = await client.get(
            "/api/events",
            params={
                "from": "2026-08-01T00:00:00-03:00",
                "to": "2026-08-31T23:59:59-03:00",
                "status": "scheduled",
            },
        )

    assert filtered.status_code == 200
    assert [item["title"] for item in filtered.json()] == ["Entrevista no período"]
