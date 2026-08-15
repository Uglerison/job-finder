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
async def test_filter_api_returns_accepted_jobs_and_traceable_exclusions(application) -> None:
    transport = ASGITransport(app=application)
    payload = {
        "criteria": {
            "target_roles": ["Backend Engineer"],
            "weights": {"skills": 40, "experience": 35, "location": 25},
            "restrictions": {
                "countries": ["Brasil"],
                "work_models": ["remote"],
                "contract_types": ["full_time"],
                "excluded_keywords": ["estágio"],
            },
        },
        "jobs": [
            {
                "id": "job-1",
                "title": "Backend Engineer",
                "description": "Python remoto",
                "country": "Brasil",
                "work_model": "remote",
                "contract_type": "full_time",
            },
            {
                "id": "job-2",
                "title": "Estágio de suporte",
                "description": "Presencial",
                "country": "Brasil",
                "work_model": "on_site",
                "contract_type": "internship",
            },
        ],
    }

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/filters/evaluate", json=payload)

    assert response.status_code == 200
    assert response.json() == [
        {"accepted": True, "exclusions": [], "job_id": "job-1"},
        {
            "accepted": False,
            "exclusions": [
                {"reason": "Regime não permitido: on_site.", "rule": "work_model"},
                {
                    "reason": "Tipo de contrato não permitido: internship.",
                    "rule": "contract_type",
                },
                {
                    "reason": "Palavra bloqueada encontrada: estágio.",
                    "rule": "blocked_keyword",
                },
            ],
            "job_id": "job-2",
        },
    ]
