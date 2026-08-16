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
async def test_manual_job_is_normalized_and_starts_as_found_with_auditable_origin(
    application,
) -> None:
    transport = ASGITransport(app=application)
    payload = {
        "canonical_url": " HTTPS://Example.com/jobs//backend/?utm_source=manual ",
        "title": " Backend\n Engineer ",
        "company": " Example\t Labs ",
        "location": " São   Paulo, SP ",
        "raw_content": "<p>Descrição original da vaga</p>",
    }

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/jobs", json=payload)

    body = response.json()
    assert response.status_code == 201
    assert body["status"] == "found"
    assert body["status_label"] == "ENCONTRADA"
    assert body["canonical_url"] == "https://example.com/jobs/backend"
    assert body["title"] == "Backend Engineer"
    assert body["company"] == "Example Labs"
    assert body["origins"] == [
        {
            "external_id": None,
            "id": body["origins"][0]["id"],
            "source": "manual",
            "url": "https://example.com/jobs/backend",
        },
    ]
    assert body["content_versions"][0]["raw_content"] == payload["raw_content"]


@pytest.mark.anyio
async def test_manual_job_rejects_invalid_url_and_missing_required_fields(application) -> None:
    transport = ASGITransport(app=application)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        invalid_url = await client.post(
            "/api/jobs",
            json={
                "canonical_url": "javascript:alert(1)",
                "title": "Backend Engineer",
                "company": "Example Labs",
                "raw_content": "descrição",
            },
        )
        missing_title = await client.post(
            "/api/jobs",
            json={
                "canonical_url": "https://example.com/jobs/1",
                "company": "Example Labs",
                "raw_content": "descrição",
            },
        )

    assert invalid_url.status_code == 422
    assert missing_title.status_code == 422
