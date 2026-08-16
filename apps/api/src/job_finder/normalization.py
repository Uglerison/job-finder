"""Deterministic normalization for job fields before persistence or matching."""

import re
import unicodedata
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict

from job_finder.jobs import JobDraft

_TRACKING_QUERY_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid"}


class RawJobData(BaseModel):
    """Untrusted job data that still needs canonical representation."""

    model_config = ConfigDict(extra="forbid")

    canonical_url: str | None = None
    title: str
    company: str
    location: str | None = None
    published_at: datetime | None = None
    expires_at: datetime | None = None


def normalize_job(data: RawJobData) -> JobDraft:
    """Return the same normalized representation for equivalent raw inputs."""

    published_at = _normalize_datetime(data.published_at, "published_at")
    expires_at = _normalize_datetime(data.expires_at, "expires_at")
    if published_at is not None and expires_at is not None and expires_at < published_at:
        raise ValueError("expires_at must be greater than or equal to published_at")

    return JobDraft(
        canonical_url=normalize_url(data.canonical_url),
        title=normalize_text(data.title, "title"),
        company=normalize_text(data.company, "company"),
        location=normalize_text(data.location, "location") if data.location else None,
        published_at=published_at,
        expires_at=expires_at,
    )


def normalize_text(value: str, field_name: str = "text") -> str:
    """Collapse Unicode whitespace without changing user-visible letter casing."""

    normalized = " ".join(unicodedata.normalize("NFKC", value).split())
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def normalize_url(value: str | None) -> str | None:
    """Canonicalize a public HTTP(S) URL and remove common tracking parameters."""

    if value is None:
        return None

    raw_url = value.strip()
    parsed = urlsplit(raw_url)
    scheme = parsed.scheme.casefold()
    if scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("canonical_url must use an http or https scheme")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("canonical_url must not contain credentials")

    try:
        port = parsed.port
    except ValueError as error:
        raise ValueError("canonical_url contains an invalid port") from error

    hostname = parsed.hostname.casefold().rstrip(".")
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    if port is not None and port not in ({"http": 80, "https": 443}[scheme],):
        hostname = f"{hostname}:{port}"

    path = re.sub(r"/{2,}", "/", parsed.path or "")
    if len(path) > 1:
        path = path.rstrip("/")

    query_values = [
        (key, query_value)
        for key, query_value in parse_qsl(parsed.query, keep_blank_values=True)
        if not _is_tracking_key(key)
    ]
    query_values.sort(key=lambda item: (item[0].casefold(), item[1]))
    query = urlencode(query_values, doseq=True)
    return urlunsplit((scheme, hostname, path, query, ""))


def _is_tracking_key(key: str) -> bool:
    folded = key.casefold()
    return folded.startswith("utm_") or folded in _TRACKING_QUERY_KEYS


def _normalize_datetime(value: datetime | None, field_name: str) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
