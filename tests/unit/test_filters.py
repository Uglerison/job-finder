from job_finder.filters import JobSnapshot, evaluate_job
from job_finder.profile_criteria import ProfileCriteria


def test_mandatory_filters_return_traceable_exclusion_reasons() -> None:
    criteria = ProfileCriteria.model_validate(
        {
            "target_roles": ["Backend Engineer"],
            "skills": ["Python"],
            "languages": [],
            "salary_expectation": {
                "currency": "BRL",
                "minimum_monthly": 10000,
                "maximum_monthly": 15000,
            },
            "weights": {"skills": 40, "experience": 35, "location": 25},
            "restrictions": {
                "countries": ["Brasil"],
                "work_models": ["remote"],
                "contract_types": ["full_time"],
                "locations": [],
                "excluded_keywords": ["estágio"],
            },
        },
    )

    result = evaluate_job(
        JobSnapshot(
            contract_type="internship",
            country="Estados Unidos",
            description="Vaga presencial para estágio em suporte.",
            maximum_monthly=8000,
            minimum_monthly=5000,
            salary_currency="BRL",
            title="Estágio em suporte",
            work_model="on_site",
        ),
        criteria,
    )

    assert result.accepted is False
    assert [item.rule for item in result.exclusions] == [
        "country",
        "work_model",
        "contract_type",
        "salary",
        "blocked_keyword",
    ]
    assert "Estados Unidos" in result.exclusions[0].reason
    assert "estágio" in result.exclusions[-1].reason


def test_mandatory_filters_accept_a_job_that_meets_every_constraint() -> None:
    criteria = ProfileCriteria.model_validate(
        {
            "target_roles": ["Backend Engineer"],
            "weights": {"skills": 40, "experience": 35, "location": 25},
            "restrictions": {
                "countries": ["Brasil"],
                "work_models": ["remote"],
                "contract_types": ["full_time"],
            },
        },
    )

    result = evaluate_job(
        JobSnapshot(
            contract_type="full_time",
            country="Brasil",
            description="Backend com Python.",
            title="Backend Engineer",
            work_model="remote",
        ),
        criteria,
    )

    assert result.accepted is True
    assert result.exclusions == []
