"""Deterministic helpers for selective, auditable vacancy discovery."""

from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, Field

from job_finder.source_adapters import SourceCandidate


class DiscoveryCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    company: str
    location: str | None
    url: str
    source_key: str
    evidence: str = Field(max_length=500)


def select_candidates(
    candidates: Iterable[SourceCandidate],
    limit: int,
) -> list[DiscoveryCandidate]:
    """Deduplicate by canonical URL and bound results before presenting them to a person."""

    selected: list[DiscoveryCandidate] = []
    seen: set[str] = set()
    for candidate in candidates:
        if len(selected) >= max(1, limit):
            break
        url = candidate.url.strip()
        if not url or url in seen:
            continue
        seen.add(url)
        selected.append(
            DiscoveryCandidate(
                title=candidate.title,
                company=candidate.company,
                location=candidate.location,
                url=url,
                source_key=candidate.source_key,
                evidence=(candidate.description or candidate.title).strip()[:500],
            )
        )
    return selected
