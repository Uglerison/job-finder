from job_finder.ai_prompts import (
    ANALYSIS_PROMPT_VERSION,
    analysis_configuration,
    render_analysis_instructions,
)
from job_finder.profile_criteria import ProfileCriteria


def make_profile() -> ProfileCriteria:
    return ProfileCriteria.model_validate(
        {
            "languages": [{"code": "pt-br", "minimum_level": "professional"}],
            "restrictions": {
                "contract_types": ["full_time"],
                "countries": ["Brazil"],
                "excluded_keywords": ["vendas"],
                "locations": ["Curitiba"],
                "work_models": ["remote", "hybrid"],
            },
            "salary_expectation": None,
            "skills": ["SQL", "contato@example.com"],
            "target_roles": ["Data Analyst"],
            "weights": {"location": 20, "skills": 80},
        }
    )


def test_analysis_prompt_is_deterministic_versioned_and_redacts_profile_data() -> None:
    profile = make_profile()

    first = render_analysis_instructions(profile)
    second = render_analysis_instructions(profile)

    assert first == second
    assert ANALYSIS_PROMPT_VERSION in first
    assert "contato@example.com" not in first
    assert "[E-MAIL REMOVIDO]" in first
    assert "Não use atributos sensíveis" in first
    assert "citação exata" in first


def test_analysis_configuration_uses_low_for_volume_and_medium_for_detailed_reviews() -> None:
    batch = analysis_configuration("batch")
    detailed = analysis_configuration("detailed")

    assert batch.version == ANALYSIS_PROMPT_VERSION
    assert batch.reasoning_effort == "low"
    assert detailed.reasoning_effort == "medium"
