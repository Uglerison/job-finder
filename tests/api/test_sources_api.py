from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from job_finder.database import create_database_engine, create_session_factory, run_migrations
from job_finder.main import create_app
from job_finder.settings import Settings
from job_finder.source_adapters import SourceCandidate, SourceSearchResult


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def application(tmp_path: Path):
    run_migrations(tmp_path)
    app = create_app(Settings(data_dir=tmp_path, environment="test"))
    app.state.session_factory = create_session_factory(create_database_engine(tmp_path))
    return app


class FakeAdapter:
    source_key = "remoteok"

    def __init__(self) -> None:
        self.calls = 0

    async def search(self, request):
        self.calls += 1
        request.cancellation.raise_if_cancelled()
        return SourceSearchResult(
            (
                SourceCandidate(
                    source_key=self.source_key,
                    external_id="fake-1",
                    url="https://source.example/jobs/fake-1",
                    title="Backend Engineer",
                    company="Example Labs",
                    location="Remote",
                    description="Python and FastAPI",
                ),
            )[: request.limit],
        )


@pytest.mark.anyio
async def test_sources_are_seeded_and_update_without_exposing_secrets(application) -> None:
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        listed = await client.get("/api/sources")
        updated = await client.put(
            "/api/sources/remoteok",
            json={
                "display_name": "Remote OK custom",
                "endpoint": "https://remoteok.com/api",
                "terms_url": "https://remoteok.com/terms",
                "enabled": True,
                "schedule_enabled": True,
                "frequency_minutes": 60,
                "daily_limit": 10,
                "per_run_limit": 5,
                "timeout_seconds": 10,
            },
        )

    assert listed.status_code == 200
    assert {item["source_key"] for item in listed.json()} == {"remoteok", "arbeitnow", "jobicy"}
    assert updated.status_code == 200
    assert updated.json()["frequency_minutes"] == 60
    assert "secret_ref" not in updated.json()


@pytest.mark.anyio
async def test_search_run_persists_counters_and_exact_duplicate_on_second_run(application) -> None:
    adapter = FakeAdapter()
    application.state.source_registry.register(adapter)
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        await client.get("/api/sources")
        first = await client.post(
            "/api/search-runs?wait=true",
            json={"source_key": "remoteok", "query": "backend", "limit": 10},
        )
        second = await client.post(
            "/api/search-runs?wait=true",
            json={"source_key": "remoteok", "query": "backend", "limit": 10},
        )
        runs = await client.get("/api/search-runs")

    assert first.status_code == 202
    assert first.json()["status"] == "completed"
    assert first.json()["jobs_created"] == 1
    assert second.json()["exact_duplicates"] == 1
    assert runs.json()[0]["source_key"] == "remoteok"
    assert adapter.calls == 2
