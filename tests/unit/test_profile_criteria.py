import pytest
from pydantic import ValidationError

from job_finder.profile_criteria import ProfileCriteria


def valid_criteria() -> dict[str, object]:
    return {
        "target_roles": ["Backend Engineer"],
        "skills": ["Python", "FastAPI"],
        "languages": [{"code": "en", "minimum_level": "professional"}],
        "salary_expectation": {
            "currency": "BRL",
            "minimum_monthly": 10000,
            "maximum_monthly": 15000,
        },
        "weights": {"skills": 40, "experience": 35, "location": 25},
        "restrictions": {
            "work_models": ["remote", "hybrid"],
            "locations": ["Brasil"],
            "excluded_keywords": ["internship"],
        },
    }


def test_profile_criteria_accepts_consistent_job_search_preferences() -> None:
    criteria = ProfileCriteria.model_validate(valid_criteria())

    assert criteria.salary_expectation is not None
    assert criteria.salary_expectation.currency == "BRL"
    assert criteria.weights["skills"] == 40
    assert criteria.languages[0].minimum_level == "professional"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("target_roles", ["   "]),
        ("weights", {"skills": 75, "experience": 20}),
        (
            "salary_expectation",
            {"currency": "BRL", "minimum_monthly": 15000, "maximum_monthly": 10000},
        ),
        ("languages", [{"code": "english", "minimum_level": "advanced"}]),
        (
            "restrictions",
            {"work_models": ["anywhere"], "locations": ["Brasil"], "excluded_keywords": []},
        ),
    ],
)
def test_profile_criteria_rejects_invalid_roles_weights_salary_languages_and_restrictions(
    field: str,
    value: object,
) -> None:
    payload = valid_criteria()
    payload[field] = value

    with pytest.raises(ValidationError):
        ProfileCriteria.model_validate(payload)
