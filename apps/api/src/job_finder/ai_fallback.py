"""Deterministic, clearly labelled fallback when an external AI call cannot run."""

from job_finder.ai_analysis import JobExtraction, JobFitAssessment, StructuredJobAnalysis
from job_finder.filters import JobSnapshot, evaluate_job
from job_finder.profile_criteria import ProfileCriteria


def build_fallback_analysis(
    profile: ProfileCriteria,
    *,
    title: str,
    company: str,
    location: str | None,
    raw_content: str,
    reason: str,
) -> StructuredJobAnalysis:
    """Use local metadata and deterministic filters, never infer unsupported claims."""

    decision = evaluate_job(
        JobSnapshot(
            title=title,
            location=location,
            work_model=None,
            contract_type=None,
            country=None,
            minimum_monthly=None,
            maximum_monthly=None,
            description=raw_content,
        ),
        profile,
    )
    return StructuredJobAnalysis(
        extraction=JobExtraction(
            title=title,
            company=company,
            location=location,
            work_model="unspecified",
            contract_type="unspecified",
            seniority="unspecified",
            salary_currency=None,
            salary_minimum_monthly=None,
            salary_maximum_monthly=None,
            required_skills=[],
            responsibilities=[],
            benefits=[],
        ),
        assessment=JobFitAssessment(
            score=100 if decision.accepted else 0,
            confidence=35,
            summary="Análise limitada: a triagem determinística local foi preservada.",
            strengths=[],
            gaps=[item.reason for item in decision.exclusions],
            warnings=[f"IA indisponível: {reason}"],
            evidence=[],
        ),
    )
