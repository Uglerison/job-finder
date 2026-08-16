from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from job_finder.database import create_database_engine, create_session_factory, run_migrations
from job_finder.main import create_app
from job_finder.settings import Settings


@pytest.fixture
def application(tmp_path: Path):
    run_migrations(tmp_path)
    app = create_app(Settings(data_dir=tmp_path, environment="test"))
    app.state.session_factory = create_session_factory(create_database_engine(tmp_path))
    return app


@pytest.mark.anyio
async def test_dashboard_summary_exposes_cards_funnel_series_and_source_credit(application) -> None:
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        first = await client.post(
            "/api/jobs",
            json={
                "canonical_url": "https://example.com/jobs/one",
                "title": "Backend Engineer",
                "company": "Acme",
                "location": "Remoto",
                "raw_content": "Python",
            },
        )
        second = await client.post(
            "/api/jobs",
            json={
                "canonical_url": "https://example.com/jobs/two",
                "title": "Data Analyst",
                "company": "Beta",
                "location": "Remoto",
                "raw_content": "SQL",
            },
        )
        job_id = first.json()["id"]
        application_response = await client.post(f"/api/jobs/{job_id}/application")
        application_id = application_response.json()["id"]
        await client.post(
            f"/api/applications/{application_id}/transition",
            json={"to_status": "applied"},
        )
        response = await client.get(
            "/api/dashboard/summary",
            params={
                "from": "2026-01-01",
                "to": "2026-12-31",
                "timezone": "America/Sao_Paulo",
            },
        )

    assert second.status_code == 201
    assert response.status_code == 200
    body = response.json()
    assert body["cards"]["jobs_found"] == 2
    assert body["cards"]["applications"] == 1
    assert body["funnel"][1]["denominator"] == 2
    assert body["sources"][0]["source_key"] == "manual"
    assert body["series"]


@pytest.mark.anyio
async def test_dashboard_rejects_inverted_period_and_unknown_timezone(application) -> None:
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        inverted = await client.get(
            "/api/dashboard/summary",
            params={"from": "2026-08-20", "to": "2026-08-01"},
        )
        unknown_timezone = await client.get(
            "/api/dashboard/summary",
            params={"timezone": "Mars/Colony"},
        )

    assert inverted.status_code == 422
    assert unknown_timezone.status_code == 422
