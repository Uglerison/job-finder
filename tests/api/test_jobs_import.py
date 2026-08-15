from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from job_finder.database import create_database_engine, create_session_factory, run_migrations
from job_finder.job_import import FetchedDocument
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
async def test_import_url_persists_safe_content_and_url_origin(application, monkeypatch) -> None:
    async def fake_fetch(url: str) -> FetchedDocument:
        assert url == "https://jobs.example.com/opportunities/backend-1"
        return FetchedDocument(
            url=url,
            content_type="text/html",
            body=(
                "<html><head><title>Backend Engineer</title></head>"
                "<body><p>Python</p><script>steal()</script></body></html>"
            ),
        )

    monkeypatch.setattr("job_finder.jobs_api.fetch_public_document", fake_fetch)
    transport = ASGITransport(app=application)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/jobs/import",
            json={"url": "https://jobs.example.com/opportunities/backend-1"},
        )

    body = response.json()
    assert response.status_code == 201
    assert body["title"] == "Backend Engineer"
    assert body["origins"][0]["source"] == "url_import"
    assert body["content_versions"][0]["content_type"] == "text/plain"
    assert "steal" not in body["content_versions"][0]["raw_content"]
    assert "Python" in body["content_versions"][0]["raw_content"]


@pytest.mark.anyio
async def test_import_url_rejects_blocked_destination_before_fetch(
    application,
    monkeypatch,
) -> None:
    fetch_mock = pytest.MonkeyPatch()
    fetch_mock.setattr(
        "job_finder.jobs_api.fetch_public_document",
        pytest.fail,
    )
    transport = ASGITransport(app=application)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/jobs/import",
            json={"url": "http://127.0.0.1/internal"},
        )

    fetch_mock.undo()
    assert response.status_code == 422
