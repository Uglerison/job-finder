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


async def _create_job(client: AsyncClient, slug: str, title: str, company: str) -> dict:
    response = await client.post(
        "/api/jobs",
        json={
            "canonical_url": f"https://jobs.example.com/{slug}",
            "title": title,
            "company": company,
            "raw_content": f"Descrição de {title}",
        },
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.anyio
async def test_jobs_list_supports_pagination_search_and_stable_order(application) -> None:
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        await _create_job(client, "python", "Python Developer", "Example Labs")
        await _create_job(client, "data", "Data Engineer", "Data Co")
        response = await client.get(
            "/api/jobs",
            params={"page": 1, "page_size": 1, "q": "data", "order": "title"},
        )

    body = response.json()
    assert response.status_code == 200
    assert body["total"] == 1
    assert body["page"] == 1
    assert body["page_size"] == 1
    assert body["pages"] == 1
    assert body["items"][0]["title"] == "Data Engineer"
    assert body["items"][0]["origin_count"] == 1


@pytest.mark.anyio
async def test_job_detail_returns_sources_content_and_clear_not_found(application) -> None:
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        created = await _create_job(client, "detail", "Backend Engineer", "Example Labs")
        detail = await client.get(f"/api/jobs/{created['id']}")
        missing = await client.get("/api/jobs/9999")

    body = detail.json()
    assert detail.status_code == 200
    assert body["id"] == created["id"]
    assert body["origins"][0]["source"] == "manual"
    assert body["content_versions"][0]["raw_content"] == "Descrição de Backend Engineer"
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Vaga não encontrada."
