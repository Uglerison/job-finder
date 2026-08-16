from decimal import Decimal

from job_finder.ai_budget import BudgetConfig, evaluate_budget
from job_finder.ai_cache import AnalysisPromptCache
from job_finder.ai_discovery import select_candidates
from job_finder.ai_usage import LunaPricing, summarize_usage, usage_from_response
from job_finder.openai_client import OpenAiUsage
from job_finder.profile_criteria import ProfileCriteria
from job_finder.source_adapters import SourceCandidate


def profile() -> ProfileCriteria:
    return ProfileCriteria.model_validate(
        {
            "target_roles": ["Backend Engineer"],
            "skills": ["Python"],
            "languages": [],
            "salary_expectation": None,
            "weights": {"skills": 100},
            "restrictions": {"work_models": ["remote"]},
        }
    )


def test_usage_estimates_cache_aware_cost_and_tolerates_missing_usage() -> None:
    measured = usage_from_response(
        OpenAiUsage(input_tokens=1_000, cached_input_tokens=400, output_tokens=500),
        37,
        pricing=LunaPricing(
            input_usd_per_million=Decimal("1"),
            cached_input_usd_per_million=Decimal("0.1"),
            output_usd_per_million=Decimal("2"),
        ),
    )
    assert measured.estimated_cost_usd == 0.00164
    assert measured.metered is True
    assert usage_from_response(OpenAiUsage(), 0).estimated_cost_usd is None


def test_budget_alerts_and_hard_stop_are_deterministic() -> None:
    config = BudgetConfig(monthly_budget_usd=Decimal("10"))
    assert evaluate_budget(5, config).alerts == (50,)
    assert evaluate_budget(8, config).alerts == (50, 80)
    assert evaluate_budget(10, config).blocked is True


def test_prompt_cache_is_version_scoped_and_redacts_no_job_content() -> None:
    cache = AnalysisPromptCache()
    first = cache.get(1, profile(), "batch")
    second = cache.get(1, profile(), "batch")
    other_profile_version = cache.get(2, profile(), "batch")
    assert first.hit is False
    assert second.hit is True
    assert other_profile_version.hit is False
    assert "job_description" not in first.value


def test_discovery_deduplicates_urls_and_applies_limit() -> None:
    candidates = [
        SourceCandidate("remoteok", "1", "https://example.com/a", "A", "Acme", None, "Python"),
        SourceCandidate(
            "remoteok", "2", "https://example.com/a", "A duplicate", "Acme", None, "Python"
        ),
        SourceCandidate("remoteok", "3", "https://example.com/b", "B", "Beta", "Remote", "FastAPI"),
    ]
    selected = select_candidates(candidates, 2)
    assert [item.url for item in selected] == ["https://example.com/a", "https://example.com/b"]


def test_usage_summary_is_dashboard_safe() -> None:
    summary = summarize_usage(
        [
            {
                "input_tokens": 10,
                "output_tokens": 5,
                "estimated_cost_usd": 0.01,
                "metered": True,
                "latency_ms": 20,
            },
            {"fallback": True, "latency_ms": 0},
        ]
    )
    assert summary.operations == 2
    assert summary.metered_operations == 1
    assert summary.total_estimated_cost_usd == 0.01
