from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from job_finder.main import create_app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def frontend_dist(tmp_path: Path) -> Path:
    """Create the smallest compiled frontend needed to exercise SPA delivery."""

    assets_directory = tmp_path / "assets"
    assets_directory.mkdir()
    (tmp_path / "index.html").write_text("<main>Job Finder</main>", encoding="utf-8")
    (assets_directory / "app.js").write_text("console.log('ready')", encoding="utf-8")
    return tmp_path


@pytest.mark.anyio
async def test_frontend_root_and_spa_fallback_share_the_api_origin(
    frontend_dist: Path,
) -> None:
    transport = ASGITransport(app=create_app(frontend_dist_dir=frontend_dist))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        root_response = await client.get("/")
        pipeline_response = await client.get("/pipeline")
        asset_response = await client.get("/assets/app.js")
        health_response = await client.get("/api/health")

    assert root_response.text == "<main>Job Finder</main>"
    assert pipeline_response.text == "<main>Job Finder</main>"
    assert asset_response.text == "console.log('ready')"
    assert health_response.json() == {"status": "ok", "version": "0.1.0"}
