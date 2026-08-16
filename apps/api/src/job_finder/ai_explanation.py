"""Evidence verification that keeps unsupported model statements out of factual output."""

from html.parser import HTMLParser
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from job_finder.ai_analysis import AnalysisEvidence, EvidenceSource, StructuredJobAnalysis

ExplanationCategory = Literal["summary", "strength", "gap", "warning", "evidence"]
ExplanationStatus = Literal["supported", "needs_review"]


class SupportedEvidence(BaseModel):
    """A model claim whose exact excerpt is present in its declared source text."""

    model_config = ConfigDict(extra="forbid")

    claim: str = Field(min_length=1, max_length=240)
    quote: str = Field(min_length=1, max_length=240)
    source: EvidenceSource


class ExplanationItem(BaseModel):
    """A review item that is factual only when its citations are verified locally."""

    model_config = ConfigDict(extra="forbid")

    category: ExplanationCategory
    text: str = Field(min_length=1, max_length=1_000)
    status: ExplanationStatus
    citations: list[str] = Field(default_factory=list, max_length=30)


class JobExplanation(BaseModel):
    """A traceable explanation that never silently upgrades an unsupported claim to fact."""

    model_config = ConfigDict(extra="forbid")

    summary: ExplanationItem
    strengths: list[ExplanationItem] = Field(max_length=20)
    gaps: list[ExplanationItem] = Field(max_length=20)
    warnings: list[ExplanationItem] = Field(max_length=20)
    supported_evidence: list[SupportedEvidence] = Field(max_length=30)
    unsupported_claims: list[ExplanationItem] = Field(max_length=30)


def build_explanation(
    analysis: StructuredJobAnalysis,
    *,
    title: str,
    company: str,
    location: str | None,
    raw_content: str,
) -> JobExplanation:
    """Verify every quote locally and label anything without proof for human review."""

    sources = _source_texts(title, company, location, raw_content)
    supported: list[SupportedEvidence] = []
    unsupported: list[ExplanationItem] = []
    for evidence in analysis.assessment.evidence:
        if _quote_exists(evidence, sources):
            supported.append(
                SupportedEvidence(
                    claim=evidence.claim,
                    quote=evidence.quote,
                    source=evidence.source,
                )
            )
        else:
            unsupported.append(
                ExplanationItem(
                    category="evidence",
                    text=evidence.claim,
                    status="needs_review",
                )
            )

    assessment = analysis.assessment
    return JobExplanation(
        summary=_review_item("summary", assessment.summary, supported),
        strengths=[_review_item("strength", item, supported) for item in assessment.strengths],
        gaps=[_review_item("gap", item, supported) for item in assessment.gaps],
        warnings=[_review_item("warning", item, supported) for item in assessment.warnings],
        supported_evidence=supported,
        unsupported_claims=unsupported,
    )


def _review_item(
    category: ExplanationCategory,
    text: str,
    supported_evidence: list[SupportedEvidence],
) -> ExplanationItem:
    """Attach only exact quotes repeated in the item; otherwise request human review."""

    normalized_text = _normalize(text)
    citations = [
        evidence.quote
        for evidence in supported_evidence
        if _normalize(evidence.quote) in normalized_text
    ]
    return ExplanationItem(
        category=category,
        text=text,
        status="supported" if citations else "needs_review",
        citations=citations,
    )


def _source_texts(
    title: str,
    company: str,
    location: str | None,
    raw_content: str,
) -> dict[EvidenceSource, str]:
    return {
        "job_title": title,
        "job_description": _visible_text(raw_content),
        "job_metadata": " ".join(item for item in (company, location) if item),
    }


def _quote_exists(evidence: AnalysisEvidence, sources: dict[EvidenceSource, str]) -> bool:
    return _normalize(evidence.quote) in _normalize(sources[evidence.source])


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())


def _visible_text(raw_content: str) -> str:
    """Compare citations with visible text even when an imported listing retained HTML."""

    parser = _TextExtractor()
    parser.feed(raw_content)
    parser.close()
    return " ".join(parser.parts) if parser.parts else raw_content


class _TextExtractor(HTMLParser):
    """Collect textual nodes without executing or preserving markup."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data)
