"""Deterministic, explainable filters applied before any AI ranking."""

from dataclasses import dataclass

from job_finder.profile_criteria import ProfileCriteria


@dataclass(frozen=True)
class JobSnapshot:
    """Minimal normalized job data required by mandatory filters."""

    title: str
    description: str = ""
    country: str | None = None
    work_model: str | None = None
    contract_type: str | None = None
    location: str | None = None
    minimum_monthly: int | None = None
    maximum_monthly: int | None = None
    salary_currency: str | None = None


@dataclass(frozen=True)
class FilterExclusion:
    """One deterministic exclusion and the reason shown to the user."""

    rule: str
    reason: str


@dataclass(frozen=True)
class FilterEvaluation:
    """Result of all mandatory filters for one job snapshot."""

    accepted: bool
    exclusions: list[FilterExclusion]


def evaluate_job(job: JobSnapshot, criteria: ProfileCriteria) -> FilterEvaluation:
    """Evaluate every hard constraint in a stable order and preserve all reasons."""

    restrictions = criteria.restrictions
    exclusions: list[FilterExclusion] = []

    if restrictions.countries and _normalise(job.country) not in {
        _normalise(country) for country in restrictions.countries
    }:
        exclusions.append(
            FilterExclusion(
                rule="country",
                reason=f"País fora das preferências: {job.country or 'não informado'}.",
            ),
        )

    if restrictions.work_models and job.work_model not in restrictions.work_models:
        exclusions.append(
            FilterExclusion(
                rule="work_model",
                reason=f"Regime não permitido: {job.work_model or 'não informado'}.",
            ),
        )

    if restrictions.contract_types and job.contract_type not in restrictions.contract_types:
        exclusions.append(
            FilterExclusion(
                rule="contract_type",
                reason=f"Tipo de contrato não permitido: {job.contract_type or 'não informado'}.",
            ),
        )

    if restrictions.locations and job.location:
        normalized_location = _normalise(job.location)
        if not any(
            _normalise(location) in normalized_location for location in restrictions.locations
        ):
            exclusions.append(
                FilterExclusion(
                    rule="location",
                    reason=f"Local fora das preferências: {job.location}.",
                ),
            )

    salary = criteria.salary_expectation
    if salary is not None and not _salary_overlaps(
        job,
        salary.minimum_monthly,
        salary.maximum_monthly,
        salary.currency,
    ):
        exclusions.append(
            FilterExclusion(
                rule="salary",
                reason="Faixa salarial incompatível ou não informada.",
            ),
        )

    searchable_text = _normalise(f"{job.title} {job.description}")
    for blocked_keyword in restrictions.excluded_keywords:
        if _normalise(blocked_keyword) in searchable_text:
            exclusions.append(
                FilterExclusion(
                    rule="blocked_keyword",
                    reason=f"Palavra bloqueada encontrada: {blocked_keyword}.",
                ),
            )

    return FilterEvaluation(accepted=not exclusions, exclusions=exclusions)


def _normalise(value: str | None) -> str:
    return (value or "").strip().casefold()


def _salary_overlaps(
    job: JobSnapshot,
    expected_minimum: int,
    expected_maximum: int,
    expected_currency: str,
) -> bool:
    if (
        job.minimum_monthly is None
        or job.maximum_monthly is None
        or _normalise(job.salary_currency) != _normalise(expected_currency)
    ):
        return False

    return job.maximum_monthly >= expected_minimum and job.minimum_monthly <= expected_maximum
