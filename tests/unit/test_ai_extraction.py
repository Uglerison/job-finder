import json

import pytest
from pydantic import SecretStr

from job_finder.ai_extraction import JobAnalysisError, analyze_job_content
from job_finder.ai_prompts import ANALYSIS_PROMPT_VERSION
from job_finder.openai_client import OpenAiTextResponse
from job_finder.profile_criteria import ProfileCriteria


class FakeStructuredClient:
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text
        self.received: dict[str, object] | None = None

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
        self.received = {
            "api_key": api_key,
            "input_text": input_text,
            "instructions": instructions,
            "reasoning_effort": reasoning_effort,
            "schema": schema,
            "schema_name": schema_name,
        }
        return OpenAiTextResponse(
            response_id="resp_test_123",
            model="gpt-5.6-luna",
            output_text=self.output_text,
        )


def make_profile() -> ProfileCriteria:
    return ProfileCriteria.model_validate(
        {
            "target_roles": ["Data Analyst"],
            "skills": ["SQL", "Python"],
            "languages": [],
            "salary_expectation": None,
            "weights": {"skills": 100},
            "restrictions": {"work_models": ["remote"]},
        }
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
            "required_skills": ["SQL", "Python"],
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


def test_job_content_is_redacted_and_sent_with_a_strict_complete_schema() -> None:
    client = FakeStructuredClient(json.dumps(valid_analysis()))
    api_key = SecretStr("sk-test-only-12345678901234567890")
    analysis = analyze_job_content(
        client,
        api_key,
        profile=make_profile(),
        title="Data Analyst",
        company="Example Labs",
        location="Brazil",
        raw_content=(
            "Strong SQL skills are required. Contact recruiter@example.com for details."
        ),
        mode="batch",
    )

    assert analysis.analysis.extraction.title == "Data Analyst"
    assert analysis.prompt_version == ANALYSIS_PROMPT_VERSION
    assert client.received is not None
    assert client.received["reasoning_effort"] == "low"
    assert client.received["schema_name"] == "job_analysis"
    assert "recruiter@example.com" not in client.received["input_text"]
    assert "[E-MAIL REMOVIDO]" in client.received["input_text"]
    schema = client.received["schema"]
    extraction_schema = schema["$defs"]["JobExtraction"]
    assert sorted(extraction_schema["required"]) == sorted(extraction_schema["properties"])
    assessment_schema = schema["$defs"]["JobFitAssessment"]
    assert sorted(assessment_schema["required"]) == sorted(assessment_schema["properties"])
    assert api_key.get_secret_value() not in str(client.received)


@pytest.mark.parametrize("output_text", ["not json", '{"extraction":{}}'])
def test_job_analysis_rejects_malformed_or_incomplete_model_output(output_text: str) -> None:
    with pytest.raises(JobAnalysisError, match="não pôde ser validada"):
        analyze_job_content(
            FakeStructuredClient(output_text),
            SecretStr("sk-test-only-12345678901234567890"),
            profile=make_profile(),
            title="Data Analyst",
            company="Example Labs",
            location=None,
            raw_content="Strong SQL skills are required.",
            mode="detailed",
        )
