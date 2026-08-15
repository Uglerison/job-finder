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
            "canonical_url": "https://jobs.example.com/metadata",
            "company": "Example Labs",
            "raw_content": "Descrição",
            "title": "Backend Engineer",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.anyio
async def test_notes_and_tags_are_editable_filterable_and_removable(application) -> None:
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        job_id = await _create_job(client)
        note = await client.post(f"/api/jobs/{job_id}/notes", json={"body": "Revisar salário"})
        updated_note = await client.patch(
            f"/api/jobs/{job_id}/notes/{note.json()['id']}",
            json={"body": "Revisar salário e remoto"},
        )
        tag = await client.post(f"/api/jobs/{job_id}/tags", json={"name": " Prioridade "})
        duplicate_tag = await client.post(
            f"/api/jobs/{job_id}/tags",
            json={"name": "prioridade"},
        )
        detail = await client.get(f"/api/jobs/{job_id}")
        removed_tag = await client.delete(f"/api/jobs/{job_id}/tags/prioridade")
        removed_note = await client.delete(f"/api/jobs/{job_id}/notes/{note.json()['id']}")

    assert note.status_code == 201
    assert updated_note.status_code == 200
    assert updated_note.json()["body"] == "Revisar salário e remoto"
    assert tag.status_code == 201
    assert duplicate_tag.status_code == 200
    assert duplicate_tag.json()["name"] == "prioridade"
    assert detail.json()["tags"] == ["prioridade"]
    assert detail.json()["notes"][0]["body"] == "Revisar salário e remoto"
    assert removed_tag.status_code == 204
    assert removed_note.status_code == 204


@pytest.mark.anyio
async def test_metadata_rejects_blank_body_and_unknown_job(application) -> None:
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        blank_note = await client.post("/api/jobs/999/notes", json={"body": " "})
        unknown_tag = await client.post("/api/jobs/999/tags", json={"name": "x"})

    assert blank_note.status_code == 422
    assert unknown_tag.status_code == 404
