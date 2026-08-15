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


async def _create_job(client: AsyncClient, slug: str) -> int:
    response = await client.post(
        "/api/jobs",
        json={
            "canonical_url": f"https://jobs.example.com/trash-{slug}",
            "company": "Example Labs",
            "raw_content": "Descrição",
            "title": "Backend Engineer",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.anyio
async def test_trash_api_hides_restores_and_requires_confirmation(application) -> None:
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        job_id = await _create_job(client, "recoverable")
        trashed = await client.post(f"/api/jobs/{job_id}/trash")
        visible = await client.get("/api/jobs")
        trash = await client.get("/api/trash")
        restored = await client.post(f"/api/jobs/{job_id}/restore")
        visible_after_restore = await client.get("/api/jobs")
        not_confirmed = await client.delete(f"/api/jobs/{job_id}")
        purged = await client.delete(f"/api/jobs/{job_id}?confirm=true")

    assert trashed.status_code == 200
    assert trashed.json()["deleted_at"] is not None
    assert visible.json()["total"] == 0
    assert trash.status_code == 200
    assert trash.json()[0]["id"] == job_id
    assert restored.status_code == 200
    assert visible_after_restore.json()["total"] == 1
    assert not_confirmed.status_code == 400
    assert purged.status_code == 204


@pytest.mark.anyio
async def test_trash_api_protects_linked_application(application) -> None:
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        job_id = await _create_job(client, "linked")
        created = await client.post(f"/api/jobs/{job_id}/application")
        response = await client.delete(f"/api/jobs/{job_id}?confirm=true")

    assert created.status_code == 201
    assert response.status_code == 409
