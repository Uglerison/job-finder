from job_finder.ai_analysis import StructuredJobAnalysis
from job_finder.ai_scoring import calculate_hybrid_fit
from job_finder.profile_criteria import ProfileCriteria


def make_analysis(
    *,
    model_score: int = 40,
    model_confidence: int = 70,
    work_model: str = "remote",
) -> StructuredJobAnalysis:
    return StructuredJobAnalysis.model_validate(
        {
            "extraction": {
                "title": "Data Analyst",
                "company": "Example Labs",
                "location": "Brazil",
                "work_model": work_model,
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
                "score": model_score,
                "confidence": model_confidence,
                "summary": "Aderência parcial.",
                "strengths": [],
                "gaps": [],
                "warnings": [],
                "evidence": [],
            },
        }
    )


def make_profile(*, weights: dict[str, int], work_model: str = "remote") -> ProfileCriteria:
    return ProfileCriteria.model_validate(
        {
            "target_roles": ["Data Analyst"],
            "skills": ["SQL", "Python"],
            "languages": [],
            "salary_expectation": None,
            "weights": weights,
            "restrictions": {
                "work_models": [work_model],
                "contract_types": ["full_time"],
            },
        }
    )


def test_hybrid_score_combines_configured_deterministic_weights_with_limited_model_signal() -> None:
    result = calculate_hybrid_fit(
        make_profile(weights={"role": 40, "skills": 60}),
        make_analysis(model_score=40, model_confidence=70),
        description="Strong SQL skills are required.",
    )

    assert result.accepted is True
    assert result.deterministic_score == 70
    assert result.model_score == 40
    assert result.score == 64
    assert result.confidence == 85
    assert [(item.name, item.score, item.weight) for item in result.components] == [
        ("role", 100, 40),
        ("skills", 50, 60),
        ("model_context", 40, 20),
    ]


def test_hybrid_score_returns_zero_for_a_deterministic_blocking_filter() -> None:
    result = calculate_hybrid_fit(
        make_profile(weights={"role": 40, "skills": 60}, work_model="remote"),
        make_analysis(work_model="on_site"),
        description="Data analysis vacancy.",
    )

    assert result.accepted is False
    assert result.score == 0
    assert result.confidence == 100
    assert [item.rule for item in result.exclusions] == ["work_model"]
    assert result.components == []


def test_hybrid_score_ignores_sensitive_or_unknown_weight_labels() -> None:
    result = calculate_hybrid_fit(
        make_profile(weights={"idade": 50, "skills": 50}),
        make_analysis(model_score=80, model_confidence=80),
        description="Strong SQL skills are required.",
    )

    assert [item.name for item in result.components] == ["skills", "model_context"]
    assert result.deterministic_score == 50
    assert result.score == 56
    assert result.confidence == 90
