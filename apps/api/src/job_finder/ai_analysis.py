"""Validated structured contracts for extracting and assessing one job listing."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

AnalysisText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=1_000),
]
ShortAnalysisText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=240),
]
CurrencyCode = Annotated[
    str,
    StringConstraints(to_upper=True, pattern=r"^[A-Z]{3}$"),
]
WorkModel = Literal["remote", "hybrid", "on_site", "unspecified"]
ContractType = Literal[
    "full_time",
    "part_time",
    "contract",
    "temporary",
    "internship",
    "unspecified",
]
Seniority = Literal["intern", "junior", "mid", "senior", "staff", "lead", "unspecified"]
EvidenceSource = Literal["job_title", "job_description", "job_metadata"]


class AnalysisEvidence(BaseModel):
    """One claim anchored in a bounded excerpt from the supplied job listing."""

    model_config = ConfigDict(extra="forbid")

    claim: ShortAnalysisText
    quote: ShortAnalysisText
    source: EvidenceSource


class JobExtraction(BaseModel):
    """Fields extracted from a vacancy while preserving unknown values explicitly."""

    model_config = ConfigDict(extra="forbid")

    title: ShortAnalysisText | None = None
    company: ShortAnalysisText | None = None
    location: ShortAnalysisText | None = None
    work_model: WorkModel = "unspecified"
    contract_type: ContractType = "unspecified"
    seniority: Seniority = "unspecified"
    salary_currency: CurrencyCode | None = None
    salary_minimum_monthly: int | None = Field(default=None, ge=1, le=10_000_000)
    salary_maximum_monthly: int | None = Field(default=None, ge=1, le=10_000_000)
    required_skills: list[ShortAnalysisText] = Field(default_factory=list, max_length=50)
    responsibilities: list[AnalysisText] = Field(default_factory=list, max_length=50)
    benefits: list[AnalysisText] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def salary_range_must_be_consistent(self) -> "JobExtraction":
        if (
            self.salary_minimum_monthly is not None
            and self.salary_maximum_monthly is not None
            and self.salary_minimum_monthly > self.salary_maximum_monthly
        ):
            raise ValueError("salary minimum cannot exceed maximum")
        return self


class JobFitAssessment(BaseModel):
    """Bounded, explainable assessment to combine with deterministic filters later."""

    model_config = ConfigDict(extra="forbid")

    score: int = Field(ge=0, le=100)
    confidence: int = Field(ge=0, le=100)
    summary: AnalysisText
    strengths: list[AnalysisText] = Field(default_factory=list, max_length=20)
    gaps: list[AnalysisText] = Field(default_factory=list, max_length=20)
    warnings: list[AnalysisText] = Field(default_factory=list, max_length=20)
    evidence: list[AnalysisEvidence] = Field(default_factory=list, max_length=30)


class StructuredJobAnalysis(BaseModel):
    """Top-level schema required before an AI extraction or assessment can be retained."""

    model_config = ConfigDict(extra="forbid")

    extraction: JobExtraction
    assessment: JobFitAssessment
