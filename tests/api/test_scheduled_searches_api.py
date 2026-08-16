import asyncio
from datetime import datetime, timezone
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from job_finder.database import create_database_engine, create_session_factory, run_migrations
from job_finder.main import create_app
from job_finder.scheduled_searches import ScheduledSearchRecord, utc_now
from job_finder.settings import Settings
from job_finder.source_adapters import SourceCandidate, SourceSearchResult


@pytest.fixture
def application(tmp_path: Path):
    run_migrations(tmp_path)
    app = create_app(Settings(data_dir=tmp_path, environment="test"))
    app.state.session_factory = create_session_factory(create_database_engine(tmp_path))
    return app


class FakeProvider:
    provider_key = "scheduled-fake"
    display_name = "Fonte agendada"

    async def search(self, params, cancellation=None):
        return SourceSearchResult(
            (
                SourceCandidate(
                    source_key="scheduled-fake",
                    external_id="scheduled-1",
                    url="https://jobs.example/scheduled-1",
                    title="Analista de Dados",
                    company="Dados Brasil",
                    location="Curitiba, PR",
                    description="Python e SQL",
                    published_at=datetime.now(timezone.utc),
                ),
            ),
        )


async def _wait_for_run(client: AsyncClient, schedule_id: int) -> dict[str, object]:
    for _ in range(20):
        response = await client.get(f"/api/scheduled-searches/{schedule_id}/runs")
        runs = response.json()
        if runs and runs[0]["status"] not in {"pending", "running"}:
            return runs[0]
        await asyncio.sleep(0.02)
    raise AssertionError("A execução agendada não terminou a tempo.")


@pytest.mark.anyio
async def test_scheduled_search_can_be_created_edited_paused_and_deleted(application) -> None:
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        created = await client.post(
            "/api/scheduled-searches",
            json={
                "name": "Dados em Curitiba",
                "query": "Analista de Dados",
                "location": "Curitiba, PR",
                "frequency_minutes": 60,
            },
        )
        updated = await client.put(
            f"/api/scheduled-searches/{created.json()['id']}",
            json={
                "name": "Dados remotos",
                "query": "Analista de Dados",
                "location": None,
                "work_model": "remote",
                "frequency_minutes": 120,
                "enabled": True,
            },
        )
        paused = await client.put(
            f"/api/scheduled-searches/{created.json()['id']}",
            json={
                "name": "Dados remotos",
                "query": "Analista de Dados",
                "location": None,
                "work_model": "remote",
                "frequency_minutes": 120,
                "enabled": False,
            },
        )
        invalid = await client.put(
            f"/api/scheduled-searches/{created.json()['id']}",
            json={
                "name": "Dados remotos",
                "query": "A",
                "frequency_minutes": 120,
                "enabled": False,
            },
        )
        deleted = await client.delete(f"/api/scheduled-searches/{created.json()['id']}")

    assert created.status_code == 201
    assert created.json()["enabled"] is False
    assert updated.status_code == 200
    assert updated.json()["work_model"] == "remote"
    assert updated.json()["next_run_at"] is not None
    assert paused.status_code == 200
    assert paused.json()["next_run_at"] is None
    assert invalid.status_code == 422
    assert deleted.status_code == 204


@pytest.mark.anyio
async def test_tick_persists_jobs_links_history_and_does_not_regress_application(
    application,
) -> None:
    application.state.aggregated_providers = [FakeProvider()]
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        created = await client.post(
            "/api/scheduled-searches",
            json={
                "name": "Busca diária",
                "query": "Analista de Dados",
                "enabled": True,
                "frequency_minutes": 15,
            },
        )
        schedule_id = created.json()["id"]
        tick = await client.post("/api/scheduled-searches/tick")
        first_run = await _wait_for_run(client, schedule_id)
        jobs = await client.get(f"/api/scheduled-searches/{schedule_id}/jobs")
        job_id = jobs.json()[0]["job_id"]
        applied = await client.post(f"/api/jobs/{job_id}/application/applied")
        with application.state.session_factory() as session:
            schedule = session.get(ScheduledSearchRecord, schedule_id)
            assert schedule is not None
            schedule.next_run_at = utc_now()
            session.commit()
        second_tick = await client.post("/api/scheduled-searches/tick")
        second_run = await _wait_for_run(client, schedule_id)
        application_after = await client.get(f"/api/jobs/{job_id}/application")

    assert tick.status_code == 200
    assert tick.json()["run_ids"]
    assert first_run["status"] == "completed"
    assert first_run["jobs_created"] == 1
    assert jobs.json()[0]["outcome"] == "created"
    assert applied.status_code == 200
    assert second_tick.json()["run_ids"]
    assert second_run["exact_duplicates"] == 1
    assert application_after.json()["current_status"] == "applied"
