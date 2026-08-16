"""Deterministic-first hybrid scoring for an already validated job analysis."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from job_finder.ai_analysis import StructuredJobAnalysis
from job_finder.filters import FilterExclusion, JobSnapshot, evaluate_job
from job_finder.profile_criteria import ProfileCriteria

FitDimension = Literal[
    "role",
    "skills",
    "location",
    "work_model",
    "contract_type",
    "salary",
    "model_context",
]

_WEIGHT_ALIASES: dict[str, FitDimension] = {
    "role": "role",
    "title": "role",
    "target_roles": "role",
    "skills": "skills",
    "location": "location",
    "country": "location",
    "work_model": "work_model",
    "regime": "work_model",
    "contract": "contract_type",
    "contract_type": "contract_type",
    "salary": "salary",
    "remuneration": "salary",
}
_MODEL_INFLUENCE = 20


class FitComponent(BaseModel):
    """One permitted, visible contribution to the score; sensitive labels are absent."""

    model_config = ConfigDict(extra="forbid")

    name: FitDimension
    score: int = Field(ge=0, le=100)
    weight: int = Field(ge=1, le=100)


class FitExclusion(BaseModel):
    """A pre-existing deterministic exclusion preserved for the score response."""

    model_config = ConfigDict(extra="forbid")

    rule: str
    reason: str


class HybridFitScore(BaseModel):
    """Auditable result that keeps deterministic constraints ahead of model context."""

    model_config = ConfigDict(extra="forbid")

    accepted: bool
    score: int = Field(ge=0, le=100)
    confidence: int = Field(ge=0, le=100)
    deterministic_score: int = Field(ge=0, le=100)
    model_score: int = Field(ge=0, le=100)
    components: list[FitComponent]
    exclusions: list[FitExclusion]


def calculate_hybrid_fit(
    criteria: ProfileCriteria,
    analysis: StructuredJobAnalysis,
    *,
    description: str,
) -> HybridFitScore:
    """Combine allowed profile weights with only a capped, secondary model signal."""

    extraction = analysis.extraction
    filter_result = evaluate_job(
        JobSnapshot(
            title=extraction.title or "Vaga sem cargo informado",
            description=description,
            country=extraction.location,
            work_model=extraction.work_model,
            contract_type=extraction.contract_type,
            location=extraction.location,
            minimum_monthly=extraction.salary_minimum_monthly,
            maximum_monthly=extraction.salary_maximum_monthly,
            salary_currency=extraction.salary_currency,
        ),
        criteria,
    )
    exclusions = [_fit_exclusion(item) for item in filter_result.exclusions]
    if not filter_result.accepted:
        return HybridFitScore(
            accepted=False,
            score=0,
            confidence=100,
            deterministic_score=0,
            model_score=analysis.assessment.score,
            components=[],
            exclusions=exclusions,
        )

    weighted_components = _weighted_components(criteria, analysis)
    if not weighted_components:
        return HybridFitScore(
            accepted=True,
            score=analysis.assessment.score,
            confidence=analysis.assessment.confidence,
            deterministic_score=analysis.assessment.score,
            model_score=analysis.assessment.score,
            components=[
                FitComponent(
                    name="model_context",
                    score=analysis.assessment.score,
                    weight=100,
                )
            ],
            exclusions=[],
        )

    total_weight = sum(weight for _, _, weight in weighted_components)
    deterministic_score = round(
        sum(score * weight for _, score, weight in weighted_components) / total_weight
    )
    score = round(
        deterministic_score * (100 - _MODEL_INFLUENCE) / 100
        + analysis.assessment.score * _MODEL_INFLUENCE / 100
    )
    components = [
        FitComponent(name=name, score=component_score, weight=weight)
        for name, component_score, weight in weighted_components
    ]
    components.append(
        FitComponent(
            name="model_context",
            score=analysis.assessment.score,
            weight=_MODEL_INFLUENCE,
        )
    )
    return HybridFitScore(
        accepted=True,
        score=score,
        confidence=round((analysis.assessment.confidence + 100) / 2),
        deterministic_score=deterministic_score,
        model_score=analysis.assessment.score,
        components=components,
        exclusions=[],
    )


def _weighted_components(
    criteria: ProfileCriteria,
    analysis: StructuredJobAnalysis,
) -> list[tuple[FitDimension, int, int]]:
    """Resolve only the explicit allowlist of job-relevant, non-sensitive dimensions."""

    components: list[tuple[FitDimension, int, int]] = []
    already_seen: set[FitDimension] = set()
    for label, weight in criteria.weights.items():
        dimension = _WEIGHT_ALIASES.get(label.strip().casefold())
        if dimension is None or dimension in already_seen:
            continue
        component_score = _component_score(dimension, criteria, analysis)
        if component_score is None:
            continue
        components.append((dimension, component_score, weight))
        already_seen.add(dimension)
    return components


def _component_score(
    dimension: FitDimension,
    criteria: ProfileCriteria,
    analysis: StructuredJobAnalysis,
) -> int | None:
    """Calculate one direct comparison without inferring sensitive personal attributes."""

    extraction = analysis.extraction
    if dimension == "role":
        return _role_score(criteria.target_roles, extraction.title)
    if dimension == "skills":
        return _skills_score(criteria.skills, extraction.required_skills)
    if dimension == "location":
        return 100 if criteria.restrictions.locations or criteria.restrictions.countries else None
    if dimension == "work_model":
        return 100 if criteria.restrictions.work_models else None
    if dimension == "contract_type":
        return 100 if criteria.restrictions.contract_types else None
    if dimension == "salary":
        return 100 if criteria.salary_expectation is not None else None
    return None


def _role_score(target_roles: list[str], extracted_title: str | None) -> int:
    """Compare normalized target-role words with the title stated in the listing."""

    if not extracted_title:
        return 0
    title_words = set(_words(extracted_title))
    scores = []
    for role in target_roles:
        role_words = set(_words(role))
        if not role_words:
            continue
        scores.append(round(100 * len(role_words & title_words) / len(role_words)))
    return max(scores, default=0)


def _skills_score(profile_skills: list[str], required_skills: list[str]) -> int | None:
    """Measure how many explicitly requested skills match profile skills."""

    if not profile_skills:
        return None
    normalized_required = [_normalize(item) for item in required_skills]
    matches = sum(
        any(skill in required or required in skill for required in normalized_required)
        for skill in (_normalize(item) for item in profile_skills)
    )
    return round(100 * matches / len(profile_skills))


def _fit_exclusion(exclusion: FilterExclusion) -> FitExclusion:
    return FitExclusion(rule=exclusion.rule, reason=exclusion.reason)


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())


def _words(value: str) -> list[str]:
    return [word for word in _normalize(value).replace("-", " ").split() if word]
