import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from job_finder.database import create_database_engine, create_session_factory, run_migrations
from job_finder.main import create_app
from job_finder.openai_client import OpenAiTextResponse
from job_finder.settings import Settings


class FakeEncryptedVault:
    def __init__(self, key: str | None) -> None:
        self.key = key

    def has_openai_api_key(self) -> bool:
        return self.key is not None

    def get_unlocked_openai_api_key(self) -> str | None:
        return self.key


class FakeStructuredClient:
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text
        self.received_input: str | None = None
        self.received_reasoning_effort: str | None = None

    def create_structured_response(
        self,
        api_key: SecretStr,
        *,
        instructions: str,
        input_text: str,
        schema_name: str,
        schema: dict[str, object],
        reasoning_effort: str,
    ) -> OpenAiTextResponse:
        self.received_input = input_text
        self.received_reasoning_effort = reasoning_effort
        return OpenAiTextResponse(
            response_id="resp_test_123",
            model="gpt-5.6-luna",
            output_text=self.output_text,
        )


def valid_analysis() -> dict[str, object]:
    return {
        "extraction": {
            "title": "Data Analyst",
            "company": "Example Labs",
            "location": "Brazil",
            "work_model": "remote",
            "contract_type": "full_time",
            "seniority": "mid",
            "salary_currency": None,
            "salary_minimum_monthly": None,
            "salary_maximum_monthly": None,
            "required_skills": ["SQL"],
            "responsibilities": ["Create dashboards"],
            "benefits": [],
        },
        "assessment": {
            "score": 82,
            "confidence": 90,
            "summary": "Boa aderência para análise de dados.",
            "strengths": ["SQL aparece explicitamente."],
            "gaps": [],
            "warnings": [],
            "evidence": [
                {
                    "claim": "A vaga pede SQL.",
                    "quote": "Strong SQL skills are required.",
                    "source": "job_description",
                }
            ],
        },
    }


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def application(tmp_path: Path):
    run_migrations(tmp_path)
    app = create_app(Settings(data_dir=tmp_path, environment="test"))
    app.state.session_factory = create_session_factory(create_database_engine(tmp_path))
    app.state.secret_vault = FakeEncryptedVault("sk-test-only-12345678901234567890")
    app.state.openai_client = FakeStructuredClient(json.dumps(valid_analysis()))
    return app


async def create_profile_and_job(client: AsyncClient) -> int:
    profile = await client.put(
        "/api/profile",
        json={
            "target_roles": ["Data Analyst"],
            "skills": ["SQL"],
            "languages": [],
            "salary_expectation": None,
            "weights": {"skills": 100},
            "restrictions": {"work_models": ["remote"]},
        },
    )
    job = await client.post(
        "/api/jobs",
        json={
            "canonical_url": "https://example.com/jobs/data-analyst",
            "title": "Data Analyst",
            "company": "Example Labs",
            "location": "Brazil",
            "raw_content": (
                "Strong SQL skills are required. Send questions to recruiter@example.com."
            ),
        },
    )
    assert profile.status_code == 200
    assert job.status_code == 201
    return job.json()["id"]


@pytest.mark.anyio
async def test_job_analysis_uses_the_current_profile_and_returns_validated_extraction(
    application,
) -> None:
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        job_id = await create_profile_and_job(client)
        response = await client.post(f"/api/jobs/{job_id}/analysis", json={"mode": "batch"})

    body = response.json()
    fake_client = application.state.openai_client
    assert response.status_code == 200
    assert body["job_id"] == job_id
    assert body["analysis"]["extraction"]["title"] == "Data Analyst"
    assert body["analysis"]["assessment"]["score"] == 82
    assert body["model"] == "gpt-5.6-luna"
    assert body["prompt_version"] == "2026-08-15.1"
    assert fake_client.received_reasoning_effort == "low"
    assert fake_client.received_input is not None
    assert "recruiter@example.com" not in fake_client.received_input
    assert "[E-MAIL REMOVIDO]" in fake_client.received_input


@pytest.mark.anyio
async def test_job_analysis_requires_a_profile_and_returns_safe_validation_errors(
    application,
) -> None:
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        job = await client.post(
            "/api/jobs",
            json={
                "canonical_url": "https://example.com/jobs/data-analyst",
                "title": "Data Analyst",
                "company": "Example Labs",
                "raw_content": "Strong SQL skills are required.",
            },
        )
        missing_profile = await client.post(f"/api/jobs/{job.json()['id']}/analysis")

        await client.put(
            "/api/profile",
            json={
                "target_roles": ["Data Analyst"],
                "skills": ["SQL"],
                "languages": [],
                "salary_expectation": None,
                "weights": {"skills": 100},
                "restrictions": {"work_models": ["remote"]},
            },
        )
        application.state.openai_client.output_text = '{"extraction":{}}'
        invalid_output = await client.post(f"/api/jobs/{job.json()['id']}/analysis")

    assert missing_profile.status_code == 409
    assert missing_profile.json() == {
        "detail": "Configure o perfil antes de analisar vagas com IA."
    }
    assert invalid_output.status_code == 502
    assert invalid_output.json() == {
        "detail": "A análise da vaga não pôde ser validada. Tente novamente."
    }
