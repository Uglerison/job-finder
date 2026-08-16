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
async def test_saved_filters_support_create_update_list_and_delete(application) -> None:
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        created = await client.post(
            "/api/saved-filters",
            json={"name": "  Remotas  ", "query": {"q": "Python", "status": "found"}},
        )
        listed = await client.get("/api/saved-filters")
        updated = await client.put(
            f"/api/saved-filters/{created.json()['id']}",
            json={"name": "Aplicar agora", "query": {"status": "applied"}},
        )
        deleted = await client.delete(f"/api/saved-filters/{created.json()['id']}")
        empty = await client.get("/api/saved-filters")

    assert created.status_code == 201
    assert created.json()["name"] == "Remotas"
    assert listed.json()[0]["query"]["q"] == "Python"
    assert updated.status_code == 200
    assert updated.json()["name"] == "Aplicar agora"
    assert deleted.status_code == 204
    assert empty.json() == []


@pytest.mark.anyio
async def test_saved_filters_reject_unknown_query_keys_and_duplicate_names(application) -> None:
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        invalid = await client.post(
            "/api/saved-filters",
            json={"name": "Inválido", "query": {"raw_sql": "drop table"}},
        )
        first = await client.post(
            "/api/saved-filters",
            json={"name": "Mesmo nome", "query": {}},
        )
        duplicate = await client.post(
            "/api/saved-filters",
            json={"name": "Mesmo nome", "query": {}},
        )

    assert invalid.status_code == 422
    assert first.status_code == 201
    assert duplicate.status_code == 409
