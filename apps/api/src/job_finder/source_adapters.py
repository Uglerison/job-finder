"""Typed source adapter contract, resilient HTTP client and public connectors."""

import asyncio
import ipaddress
import json
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Protocol, cast
from urllib.parse import urljoin, urlsplit

import httpx

from job_finder.job_import import (
    MAX_DOCUMENT_BYTES,
    MAX_REDIRECTS,
    sanitize_html,
    validate_public_url,
)
from job_finder.normalization import normalize_text, normalize_url


class SourceAdapterError(RuntimeError):
    """Base error shown in a search run without leaking response bodies or secrets."""


class SourceRateLimitError(SourceAdapterError):
    """Raised when a source asks the client to slow down."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class SourceCancelledError(SourceAdapterError):
    """Raised when a cooperative cancellation is observed."""


@dataclass
class CancellationToken:
    """Small in-process token checked between network and persistence steps."""

    cancelled: bool = False

    def cancel(self) -> None:
        self.cancelled = True

    def raise_if_cancelled(self) -> None:
        if self.cancelled:
            raise SourceCancelledError("Busca cancelada pelo usuário.")


@dataclass(frozen=True)
class SourceSearchRequest:
    """Query inputs shared by every source adapter."""

    query: str | None = None
    location: str | None = None
    limit: int = 50
    cursor: str | None = None
    cancellation: CancellationToken | None = None


@dataclass(frozen=True)
class SourceCandidate:
    """Normalized-but-not-yet-persisted job candidate returned by a source."""

    source_key: str
    external_id: str | None
    url: str
    title: str
    company: str
    location: str | None
    description: str
    published_at: datetime | None = None
    expires_at: datetime | None = None
    raw_payload: dict[str, object] = field(default_factory=dict)
    work_model: str | None = None
    salary: str | None = None
    source_label: str | None = None

    def as_payload(self) -> dict[str, object]:
        """Return a JSON-safe representation for duplicate review persistence."""

        return {
            "source_key": self.source_key,
            "external_id": self.external_id,
            "url": self.url,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "description": self.description,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "raw_payload": self.raw_payload,
            "work_model": self.work_model,
            "salary": self.salary,
            "source_label": self.source_label,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "SourceCandidate":
        """Rehydrate a candidate kept for approximate duplicate confirmation."""

        def parse_timestamp(value: object) -> datetime | None:
            if not isinstance(value, str) or not value:
                return None
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

        raw_payload = payload.get("raw_payload", {})
        if not isinstance(raw_payload, dict):
            raw_payload = {}
        return cls(
            source_key=str(payload.get("source_key", "unknown")),
            external_id=(
                str(payload["external_id"]) if payload.get("external_id") is not None else None
            ),
            url=str(payload.get("url", "")),
            title=str(payload.get("title", "")),
            company=str(payload.get("company", "")),
            location=str(payload["location"]) if payload.get("location") is not None else None,
            description=str(payload.get("description", "")),
            published_at=parse_timestamp(payload.get("published_at")),
            expires_at=parse_timestamp(payload.get("expires_at")),
            raw_payload=cast(dict[str, object], raw_payload),
            work_model=(
                str(payload["work_model"]) if payload.get("work_model") is not None else None
            ),
            salary=str(payload["salary"]) if payload.get("salary") is not None else None,
            source_label=(
                str(payload["source_label"]) if payload.get("source_label") is not None else None
            ),
        )


@dataclass(frozen=True)
class SourceSearchResult:
    """Adapter result with explicit empty/partial semantics."""

    candidates: tuple[SourceCandidate, ...]
    next_cursor: str | None = None
    partial: bool = False
    warnings: tuple[str, ...] = ()


class SourceAdapter(Protocol):
    """Contract implemented by every source connector."""

    source_key: str

    async def search(self, request: SourceSearchRequest) -> SourceSearchResult:
        """Fetch one bounded page, honoring the cancellation token."""


class SafeHttpClient:
    """HTTP client with public-destination checks, bounds, retry and backoff."""

    def __init__(
        self,
        *,
        timeout_seconds: int = 15,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Any = asyncio.sleep,
        jitter: Any | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.transport = transport
        self.sleep = sleep
        self.jitter = jitter or (lambda: random.uniform(0.0, 0.25))

    async def get_json(
        self,
        url: str,
        *,
        params: dict[str, str | int] | None = None,
        headers: dict[str, str] | None = None,
        cancellation: CancellationToken | None = None,
        max_attempts: int = 3,
    ) -> Any:
        """GET a bounded JSON response with redirect and retry policy."""

        current_url = _validate_public_http_url(url)
        timeout = httpx.Timeout(float(self.timeout_seconds), connect=min(5.0, self.timeout_seconds))
        request_headers = {"User-Agent": "JobFinder/0.1 (local job research)"}
        if headers:
            request_headers.update(headers)
        async with httpx.AsyncClient(
            timeout=timeout,
            headers=request_headers,
            follow_redirects=False,
            transport=self.transport,
        ) as client:
            redirects = 0
            attempt = 0
            while True:
                if cancellation:
                    cancellation.raise_if_cancelled()
                try:
                    response = await client.get(current_url, params=params)
                except httpx.HTTPError as error:
                    if attempt + 1 >= max_attempts:
                        raise SourceAdapterError("não foi possível acessar a fonte") from error
                    await self._wait(attempt, cancellation)
                    attempt += 1
                    continue

                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location or redirects >= MAX_REDIRECTS:
                        raise SourceAdapterError("limite de redirecionamentos da fonte excedido")
                    current_url = _validate_public_http_url(urljoin(current_url, location))
                    redirects += 1
                    continue

                if response.status_code == 429:
                    retry_after = _retry_after(response.headers.get("retry-after"))
                    if attempt + 1 >= max_attempts:
                        raise SourceRateLimitError(
                            "a fonte solicitou redução de ritmo",
                            retry_after,
                        )
                    await self._wait(attempt, cancellation, retry_after)
                    attempt += 1
                    continue

                if response.status_code >= 500 and attempt + 1 < max_attempts:
                    await self._wait(attempt, cancellation)
                    attempt += 1
                    continue
                if response.status_code >= 400:
                    raise SourceAdapterError(f"a fonte respondeu com HTTP {response.status_code}")
                if len(response.content) > MAX_DOCUMENT_BYTES:
                    raise SourceAdapterError("resposta da fonte excede o limite local")
                content_type = response.headers.get("content-type", "")
                if "json" not in content_type and not response.text.lstrip().startswith(("{", "[")):
                    raise SourceAdapterError("a fonte não retornou JSON")
                try:
                    return response.json()
                except (ValueError, json.JSONDecodeError) as error:
                    raise SourceAdapterError("JSON inválido retornado pela fonte") from error

    async def post_json(
        self,
        url: str,
        *,
        json_body: dict[str, object],
        headers: dict[str, str] | None = None,
        cancellation: CancellationToken | None = None,
        max_attempts: int = 3,
    ) -> Any:
        """POST a bounded JSON request for providers such as Jooble."""

        current_url = _validate_public_http_url(url)
        timeout = httpx.Timeout(float(self.timeout_seconds), connect=min(5.0, self.timeout_seconds))
        request_headers = {
            "User-Agent": "JobFinder/0.1 (local job research)",
            "Content-Type": "application/json",
        }
        if headers:
            request_headers.update(headers)
        async with httpx.AsyncClient(
            timeout=timeout,
            headers=request_headers,
            follow_redirects=False,
            transport=self.transport,
        ) as client:
            attempt = 0
            while True:
                if cancellation:
                    cancellation.raise_if_cancelled()
                try:
                    response = await client.post(current_url, json=json_body)
                except httpx.HTTPError as error:
                    if attempt + 1 >= max_attempts:
                        raise SourceAdapterError("não foi possível acessar a fonte") from error
                    await self._wait(attempt, cancellation)
                    attempt += 1
                    continue
                if response.status_code == 429:
                    retry_after = _retry_after(response.headers.get("retry-after"))
                    if attempt + 1 >= max_attempts:
                        raise SourceRateLimitError(
                            "a fonte solicitou redução de ritmo", retry_after
                        )
                    await self._wait(attempt, cancellation, retry_after)
                    attempt += 1
                    continue
                if response.status_code >= 500 and attempt + 1 < max_attempts:
                    await self._wait(attempt, cancellation)
                    attempt += 1
                    continue
                if response.status_code >= 400:
                    raise SourceAdapterError(f"a fonte respondeu com HTTP {response.status_code}")
                if len(response.content) > MAX_DOCUMENT_BYTES:
                    raise SourceAdapterError("resposta da fonte excede o limite local")
                try:
                    return response.json()
                except (ValueError, json.JSONDecodeError) as error:
                    raise SourceAdapterError("JSON inválido retornado pela fonte") from error

    async def _wait(
        self,
        attempt: int,
        cancellation: CancellationToken | None,
        retry_after: float | None = None,
    ) -> None:
        delay = retry_after if retry_after is not None else min(8.0, (2**attempt) + self.jitter())
        if cancellation:
            cancellation.raise_if_cancelled()
        await self.sleep(delay)


class JsonSourceAdapter:
    """Base class that keeps parsing logic separate from HTTP policy."""

    source_key = ""

    def __init__(self, endpoint: str, client: SafeHttpClient | None = None) -> None:
        self.endpoint = _validate_public_http_url(endpoint)
        self.client = client or SafeHttpClient()

    async def search(self, request: SourceSearchRequest) -> SourceSearchResult:
        payload = await self.client.get_json(
            self.endpoint,
            params=self.params(request),
            cancellation=request.cancellation,
        )
        items = self.items(payload)
        candidates: list[SourceCandidate] = []
        for item in items:
            if request.cancellation:
                request.cancellation.raise_if_cancelled()
            candidate = self.parse_item(item)
            if candidate is None:
                continue
            if request.query and request.query.casefold() not in (
                f"{candidate.title} {candidate.description}".casefold()
            ):
                continue
            if (
                request.location
                and request.location.casefold() not in (candidate.location or "").casefold()
            ):
                continue
            candidates.append(candidate)
            if len(candidates) >= request.limit:
                break
        return SourceSearchResult(tuple(candidates), partial=False)

    def params(self, request: SourceSearchRequest) -> dict[str, str | int] | None:
        return None

    def items(self, payload: Any) -> list[dict[str, object]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        return []

    def parse_item(self, item: dict[str, object]) -> SourceCandidate | None:
        raise NotImplementedError

    def _candidate(
        self,
        *,
        external_id: object,
        url: object,
        title: object,
        company: object,
        location: object,
        description: object,
        published_at: object = None,
        raw_payload: dict[str, object],
        work_model: str | None = None,
        salary: str | None = None,
        source_label: str | None = None,
    ) -> SourceCandidate | None:
        if not isinstance(url, str) or not isinstance(title, str) or not isinstance(company, str):
            return None
        canonical_url = normalize_url(url)
        if canonical_url is None:
            return None
        try:
            title_value = normalize_text(title, "title")
            company_value = normalize_text(company, "company")
        except ValueError:
            return None
        location_value = normalize_text(str(location), "location") if location else None
        description_value = sanitize_html(str(description)) if description else title_value
        return SourceCandidate(
            source_key=self.source_key,
            external_id=str(external_id) if external_id is not None else None,
            url=canonical_url,
            title=title_value,
            company=company_value,
            location=location_value,
            description=description_value,
            published_at=_parse_timestamp(published_at),
            raw_payload=raw_payload,
            work_model=work_model,
            salary=salary,
            source_label=source_label,
        )


class RemoteOkAdapter(JsonSourceAdapter):
    """Adapter for the public Remote OK JSON feed."""

    source_key = "remoteok"

    def items(self, payload: Any) -> list[dict[str, object]]:
        return [item for item in super().items(payload) if item.get("position")]

    def parse_item(self, item: dict[str, object]) -> SourceCandidate | None:
        return self._candidate(
            external_id=item.get("id"),
            url=item.get("url") or item.get("apply_url"),
            title=item.get("position"),
            company=item.get("company"),
            location=item.get("location"),
            description=item.get("description"),
            published_at=item.get("date"),
            raw_payload=item,
            work_model="remote",
            source_label="Remote OK",
        )


class ArbeitnowAdapter(JsonSourceAdapter):
    """Adapter for the public Arbeitnow job board API."""

    source_key = "arbeitnow"

    def items(self, payload: Any) -> list[dict[str, object]]:
        if isinstance(payload, dict) and isinstance(payload.get("data"), list):
            return [item for item in payload["data"] if isinstance(item, dict)]
        return []

    def parse_item(self, item: dict[str, object]) -> SourceCandidate | None:
        return self._candidate(
            external_id=item.get("slug") or item.get("id"),
            url=item.get("url"),
            title=item.get("title"),
            company=item.get("company_name"),
            location=item.get("location"),
            description=item.get("description"),
            published_at=item.get("created_at"),
            raw_payload=item,
            source_label="Arbeitnow",
        )


class JobicyAdapter(JsonSourceAdapter):
    """Adapter for the public Jobicy remote jobs JSON feed."""

    source_key = "jobicy"

    def items(self, payload: Any) -> list[dict[str, object]]:
        if isinstance(payload, dict) and isinstance(payload.get("jobs"), list):
            return [item for item in payload["jobs"] if isinstance(item, dict)]
        return []

    def parse_item(self, item: dict[str, object]) -> SourceCandidate | None:
        return self._candidate(
            external_id=item.get("id"),
            url=item.get("url"),
            title=item.get("jobTitle"),
            company=item.get("companyName"),
            location=item.get("jobGeo"),
            description=item.get("jobDescription"),
            published_at=item.get("pubDate"),
            raw_payload=item,
            work_model="remote",
            source_label="Jobicy",
        )


class SourceRegistry:
    """Registry that resolves configured source keys to adapter instances."""

    def __init__(self, adapters: dict[str, SourceAdapter] | None = None) -> None:
        self.adapters = adapters or {}

    def register(self, adapter: SourceAdapter) -> None:
        self.adapters[adapter.source_key] = adapter

    def get(self, source_key: str, endpoint: str, timeout_seconds: int) -> SourceAdapter:
        adapter = self.adapters.get(source_key)
        if adapter is not None:
            return adapter
        client = SafeHttpClient(timeout_seconds=timeout_seconds)
        if source_key == "remoteok":
            adapter = RemoteOkAdapter(endpoint, client)
        elif source_key == "arbeitnow":
            adapter = ArbeitnowAdapter(endpoint, client)
        elif source_key == "jobicy":
            adapter = JobicyAdapter(endpoint, client)
        else:
            raise SourceAdapterError(f"Nenhum adaptador registrado para {source_key}.")
        self.adapters[source_key] = adapter
        return adapter


def _validate_public_http_url(value: str) -> str:
    normalized = validate_public_url(value)
    hostname = (urlsplit(normalized).hostname or "").casefold()
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address is not None and (address.is_private or address.is_loopback or address.is_link_local):
        raise SourceAdapterError("destino da fonte bloqueado por política de rede")
    return normalized


def _parse_timestamp(value: object) -> datetime | None:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _retry_after(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return max(0.0, min(300.0, float(value)))
    except ValueError:
        try:
            target = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
        return max(0.0, (target - datetime.now(timezone.utc)).total_seconds())
