"""Typed and validated criteria used by each immutable profile version."""

from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

NonEmptyText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=120),
]
LanguageCode = Annotated[
    str,
    StringConstraints(to_lower=True, pattern=r"^[a-z]{2}(?:-[a-z]{2})?$"),
]
Percentage = Annotated[int, Field(ge=0, le=100)]
WorkModel = Literal["remote", "hybrid", "on_site"]
LanguageLevel = Literal["basic", "intermediate", "professional", "native"]


class LanguageRequirement(BaseModel):
    """Minimum proficiency required for one language in a target role."""

    model_config = ConfigDict(extra="forbid")

    code: LanguageCode
    minimum_level: LanguageLevel


class SalaryExpectation(BaseModel):
    """Expected monthly compensation range in an ISO 4217 currency."""

    model_config = ConfigDict(extra="forbid")

    currency: Annotated[str, StringConstraints(to_upper=True, pattern=r"^[A-Z]{3}$")]
    minimum_monthly: Annotated[int, Field(gt=0)]
    maximum_monthly: Annotated[int, Field(gt=0)]

    @model_validator(mode="after")
    def minimum_must_not_exceed_maximum(self) -> "SalaryExpectation":
        """Reject an inverted compensation range before it reaches persistence."""

        if self.minimum_monthly > self.maximum_monthly:
            raise ValueError("minimum_monthly must not exceed maximum_monthly")
        return self


class SearchRestrictions(BaseModel):
    """Hard constraints that a discovered job must respect."""

    model_config = ConfigDict(extra="forbid")

    work_models: list[WorkModel] = Field(min_length=1, max_length=3)
    locations: list[NonEmptyText] = Field(default_factory=list, max_length=20)
    excluded_keywords: list[NonEmptyText] = Field(default_factory=list, max_length=50)


class ProfileCriteria(BaseModel):
    """Validated job-search preferences stored in a versioned profile snapshot."""

    model_config = ConfigDict(extra="forbid")

    target_roles: list[NonEmptyText] = Field(min_length=1, max_length=20)
    skills: list[NonEmptyText] = Field(default_factory=list, max_length=100)
    languages: list[LanguageRequirement] = Field(default_factory=list, max_length=20)
    salary_expectation: SalaryExpectation | None = None
    weights: dict[NonEmptyText, Percentage] = Field(min_length=1, max_length=20)
    restrictions: SearchRestrictions

    @field_validator("weights")
    @classmethod
    def weights_must_sum_to_one_hundred(cls, weights: dict[str, int]) -> dict[str, int]:
        """Require scoring weights to form one deterministic percentage allocation."""

        if sum(weights.values()) != 100:
            raise ValueError("weights must sum to 100")
        return weights
