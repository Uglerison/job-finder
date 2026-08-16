"""Exact and reviewable approximate de-duplication for source candidates."""

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from job_finder.jobs import (
    Job,
    JobContentDraft,
    JobContentVersion,
    JobOrigin,
    JobOriginDraft,
    add_job_content_version,
    add_job_origin,
    create_job,
    get_job_content_versions,
    get_job_origins,
)
from job_finder.normalization import RawJobData, normalize_job, normalize_url
from job_finder.source_adapters import SourceCandidate
from job_finder.source_models import DuplicateSuggestionRecord, utc_now


class DedupeKind:
    """Stable outcomes used by counters and the run panel."""

    CREATED: Literal["created"] = "created"
    EXACT: Literal["exact"] = "exact"
    APPROXIMATE: Literal["approximate"] = "approximate"


@dataclass(frozen=True)
class DedupeResult:
    """Result of ingesting one candidate."""

    kind: Literal["created", "exact", "approximate"]
    job: Job | None = None
    suggestion: DuplicateSuggestionRecord | None = None
    reason: str | None = None


def ingest_candidate(
    session: Session,
    candidate: SourceCandidate,
    *,
    approximate_threshold: float = 0.82,
) -> DedupeResult:
    """Persist a candidate, attach exact origins, or pause for review."""

    exact_job, exact_reason = find_exact_match(session, candidate)
    if exact_job is not None:
        _refresh_origin(session, exact_job, candidate)
        return DedupeResult(DedupeKind.EXACT, job=exact_job, reason=exact_reason)

    approximate = find_approximate_match(session, candidate, threshold=approximate_threshold)
    if approximate is not None:
        existing_job, similarity, reasons = approximate
        suggestion = DuplicateSuggestionRecord(
            existing_job_id=existing_job.id,
            source_key=candidate.source_key,
            candidate=candidate.as_payload(),
            similarity=similarity,
            reasons=reasons,
            status="pending",
        )
        session.add(suggestion)
        session.flush()
        return DedupeResult(DedupeKind.APPROXIMATE, suggestion=suggestion)

    job = _create_candidate(session, candidate)
    return DedupeResult(DedupeKind.CREATED, job=job)


def find_exact_match(session: Session, candidate: SourceCandidate) -> tuple[Job | None, str | None]:
    """Match canonical URL, source identity, or immutable content hash."""

    normalized_url = normalize_url(candidate.url)
    if normalized_url:
        job = session.scalar(
            select(Job).where(
                Job.canonical_url == normalized_url,
                Job.deleted_at.is_(None),
            )
        )
        if job is not None:
            return job, "canonical_url"

    if candidate.external_id:
        job = session.scalar(
            select(Job)
            .join(JobOrigin, JobOrigin.job_id == Job.id)
            .where(
                JobOrigin.source == candidate.source_key,
                JobOrigin.external_id == candidate.external_id,
                Job.deleted_at.is_(None),
            ),
        )
        if job is not None:
            return job, "external_id"

    candidate_hash = content_hash(candidate.description)
    if candidate_hash:
        versions = session.scalars(select(JobContentVersion)).all()
        for version in versions:
            if content_hash(version.raw_content) == candidate_hash:
                job = session.scalar(
                    select(Job)
                    .join(JobOrigin, JobOrigin.job_id == Job.id)
                    .where(JobOrigin.id == version.origin_id, Job.deleted_at.is_(None)),
                )
                if job is not None:
                    return job, "content_hash"
    return None, None


def find_approximate_match(
    session: Session,
    candidate: SourceCandidate,
    *,
    threshold: float = 0.82,
) -> tuple[Job, float, list[str]] | None:
    """Find one likely duplicate using explainable title/company/location similarity."""

    best: tuple[Job, float, list[str]] | None = None
    for job in session.scalars(select(Job).where(Job.deleted_at.is_(None))):
        title_score = _similarity(candidate.title, job.title)
        company_score = _similarity(candidate.company, job.company)
        location_score = _similarity(candidate.location or "", job.location or "")
        score = (title_score * 0.55) + (company_score * 0.30) + (location_score * 0.15)
        reasons: list[str] = []
        if title_score >= 0.8:
            reasons.append("cargo semelhante")
        if company_score >= 0.8:
            reasons.append("empresa semelhante")
        if candidate.location and job.location and location_score >= 0.8:
            reasons.append("local semelhante")
        if score >= threshold and reasons and (best is None or score > best[1]):
            best = (job, round(score, 4), reasons)
    return best


def confirm_duplicate(session: Session, suggestion: DuplicateSuggestionRecord) -> Job:
    """Confirm a likely duplicate by attaching the new source evidence to its job."""

    if suggestion.status != "pending":
        raise ValueError("A sugestão de duplicata já foi resolvida.")
    candidate = SourceCandidate.from_payload(suggestion.candidate)
    job = session.get(Job, suggestion.existing_job_id)
    if job is None:
        raise ValueError("A vaga existente não foi encontrada.")
    _refresh_origin(session, job, candidate)
    suggestion.status = "confirmed"
    suggestion.resolved_at = utc_now()
    session.flush()
    return job


def dismiss_duplicate(session: Session, suggestion: DuplicateSuggestionRecord) -> None:
    """Dismiss a suggestion without changing the existing job."""

    if suggestion.status != "pending":
        raise ValueError("A sugestão de duplicata já foi resolvida.")
    suggestion.status = "dismissed"
    suggestion.resolved_at = utc_now()
    session.flush()


def content_hash(value: str) -> str:
    """Hash normalized content for deterministic exact duplicate detection."""

    normalized = re.sub(r"\s+", " ", value).strip().casefold()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest() if normalized else ""


def _create_candidate(session: Session, candidate: SourceCandidate) -> Job:
    draft = normalize_job(
        RawJobData(
            canonical_url=candidate.url,
            title=candidate.title,
            company=candidate.company,
            location=candidate.location,
            published_at=candidate.published_at,
            expires_at=candidate.expires_at,
        ),
    )
    job = create_job(session, draft)
    origin = add_job_origin(
        session,
        job.id,
        JobOriginDraft(
            source=candidate.source_key,
            external_id=candidate.external_id,
            url=candidate.url,
        ),
    )
    add_job_content_version(session, origin.id, _content_draft(candidate.description, utc_now()))
    return job


def _refresh_origin(session: Session, job: Job, candidate: SourceCandidate) -> None:
    origins = get_job_origins(session, job.id)
    origin = next(
        (
            item
            for item in origins
            if item.source == candidate.source_key and item.external_id == candidate.external_id
        ),
        None,
    )
    if origin is None:
        origin = add_job_origin(
            session,
            job.id,
            JobOriginDraft(
                source=candidate.source_key,
                external_id=candidate.external_id,
                url=candidate.url,
            ),
        )
    origin.last_seen_at = utc_now()
    existing_versions = get_job_content_versions(session, origin.id)
    candidate_hash = content_hash(candidate.description)
    if not any(
        content_hash(version.raw_content) == candidate_hash
        for version in existing_versions
    ):
        add_job_content_version(
            session,
            origin.id,
            _content_draft(candidate.description, utc_now()),
        )


def _similarity(left: str, right: str) -> float:
    normalized_left = re.sub(r"\s+", " ", left.casefold()).strip()
    normalized_right = re.sub(r"\s+", " ", right.casefold()).strip()
    if not normalized_left or not normalized_right:
        return 0.0
    return SequenceMatcher(None, normalized_left, normalized_right).ratio()


def _content_draft(raw_content: str, now: datetime) -> JobContentDraft:
    """Create immutable content metadata without importing the HTTP API module."""

    return JobContentDraft(
        raw_content=raw_content,
        content_type="text/html" if "<" in raw_content else "text/plain",
        captured_at=now,
        valid_from=now,
    )
