"""HTTP contract for deterministic pre-filter evaluation of job candidates."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from job_finder.filters import JobSnapshot, evaluate_job
from job_finder.profile_criteria import ProfileCriteria

router = APIRouter(prefix="/api/filters", tags=["filters"])


class JobFilterCandidate(BaseModel):
    """Normalized job fields used by the mandatory filter layer."""

    id: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(default="", max_length=20_000)
    country: str | None = Field(default=None, max_length=120)
    work_model: str | None = Field(default=None, max_length=30)
    contract_type: str | None = Field(default=None, max_length=30)
    location: str | None = Field(default=None, max_length=200)
    minimum_monthly: int | None = Field(default=None, ge=0)
    maximum_monthly: int | None = Field(default=None, ge=0)
    salary_currency: str | None = Field(default=None, max_length=3)


class FilterEvaluationRequest(BaseModel):
    """Criteria and normalized candidates evaluated in request order."""

    criteria: ProfileCriteria
    jobs: list[JobFilterCandidate] = Field(max_length=500)


class FilterExclusionResponse(BaseModel):
    """A user-visible reason why a candidate was excluded."""

    rule: str
    reason: str


class FilterEvaluationResponse(BaseModel):
    """Filter decision with all deterministic exclusion reasons."""

    job_id: str
    accepted: bool
    exclusions: list[FilterExclusionResponse]


@router.post("/evaluate", response_model=list[FilterEvaluationResponse])
def evaluate_candidates(
    payload: FilterEvaluationRequest,
) -> list[FilterEvaluationResponse]:
    """Evaluate candidates without invoking an AI model or changing state."""

    evaluations: list[FilterEvaluationResponse] = []
    for candidate in payload.jobs:
        result = evaluate_job(
            JobSnapshot(**candidate.model_dump(exclude={"id"})),
            payload.criteria,
        )
        evaluations.append(
            FilterEvaluationResponse(
                accepted=result.accepted,
                exclusions=[
                    FilterExclusionResponse(rule=item.rule, reason=item.reason)
                    for item in result.exclusions
                ],
                job_id=candidate.id,
            ),
        )

    return evaluations
