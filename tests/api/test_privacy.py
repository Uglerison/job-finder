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
async def test_redaction_api_returns_exact_safe_preview_and_replacement_counts(application) -> None:
    transport = ASGITransport(app=application)
    text = "Contato: ana@example.com, (11) 98765-4321."

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/privacy/redact", json={"text": text})

    assert response.status_code == 200
    assert response.json() == {
        "redacted_text": "Contato: [E-MAIL REMOVIDO], [TELEFONE REMOVIDO].",
        "replacements": [
            {"count": 1, "kind": "email", "token": "[E-MAIL REMOVIDO]"},
            {"count": 1, "kind": "phone", "token": "[TELEFONE REMOVIDO]"},
        ],
    }
