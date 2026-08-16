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


async def _create_job(client: AsyncClient, title: str) -> int:
    response = await client.post(
        "/api/jobs",
        json={
            "canonical_url": f"https://jobs.example.com/export-{title.replace(' ', '-')}",
            "company": "Example Labs",
            "raw_content": "Descrição",
            "title": title,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.anyio
async def test_export_api_neutralizes_csv_formulas_and_supports_json(application) -> None:
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        job_id = await _create_job(client, '=HYPERLINK("https://evil.example")')
        created = await client.post(f"/api/jobs/{job_id}/application")
        csv_response = await client.get("/api/export/jobs.csv")
        json_response = await client.get("/api/export/jobs.json", params={"status": "found"})
        applications_response = await client.get("/api/export/applications.json")

    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    assert "'=HYPERLINK" in csv_response.text
    assert "api_key" not in csv_response.text.lower()
    assert csv_response.headers["content-disposition"].endswith('filename="jobs.csv"')
    assert json_response.status_code == 200
    assert json_response.json()[0]["id"] == job_id
    assert applications_response.status_code == 200
    assert applications_response.json()[0]["id"] == created.json()["id"]
