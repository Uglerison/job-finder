"""Safe, testable URL fetching and text extraction for job listings."""

import ipaddress
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

import httpx

from job_finder.normalization import normalize_text, normalize_url

MAX_DOCUMENT_BYTES = 1_500_000
MAX_REDIRECTS = 3
_REDIRECT_STATUSES = {301, 302, 303, 307, 308}


class JobImportError(RuntimeError):
    """Raised when a public listing cannot be fetched safely."""


@dataclass(frozen=True)
class FetchedDocument:
    """A bounded document fetched from a validated public URL."""

    url: str
    content_type: str
    body: str


def validate_public_url(value: str) -> str:
    """Reject schemes and destinations that could reach local machine resources."""

    normalized = normalize_url(value)
    if normalized is None:
        raise ValueError("URL pública obrigatória")

    parsed = urlsplit(normalized)
    hostname = (parsed.hostname or "").casefold().rstrip(".")
    if not hostname:
        raise ValueError("URL pública sem host")
    if hostname in {"localhost", "localhost.localdomain", "metadata.google.internal"}:
        raise ValueError("destino local bloqueado")
    if hostname.endswith((".localhost", ".local", ".internal")):
        raise ValueError("destino local bloqueado")

    try:
        ip_address = ipaddress.ip_address(hostname)
    except ValueError:
        ip_address = None
    if ip_address is not None and (
        ip_address.is_private
        or ip_address.is_loopback
        or ip_address.is_link_local
        or ip_address.is_reserved
        or ip_address.is_multicast
        or ip_address.is_unspecified
    ):
        raise ValueError("destino de rede privada bloqueado")

    return normalized


async def fetch_public_document(url: str) -> FetchedDocument:
    """Fetch a bounded public document while validating every redirect target."""

    current_url = validate_public_url(url)
    timeout = httpx.Timeout(10.0, connect=5.0)
    headers = {"User-Agent": "JobFinder/0.1 (local job research)"}

    try:
        async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
            for redirect_count in range(MAX_REDIRECTS + 1):
                response = await client.get(current_url, follow_redirects=False)
                if response.status_code in _REDIRECT_STATUSES:
                    location = response.headers.get("location")
                    if not location:
                        raise JobImportError("redirecionamento sem destino")
                    if redirect_count == MAX_REDIRECTS:
                        raise JobImportError("limite de redirecionamentos excedido")
                    current_url = validate_public_url(urljoin(current_url, location))
                    continue

                if response.status_code >= 400:
                    raise JobImportError(f"a fonte respondeu com HTTP {response.status_code}")
                if len(response.content) > MAX_DOCUMENT_BYTES:
                    raise JobImportError("conteúdo da fonte excede o limite local")

                content_type = response.headers.get("content-type", "text/plain")
                return FetchedDocument(
                    url=current_url,
                    content_type=content_type.split(";", maxsplit=1)[0].strip().lower(),
                    body=response.content.decode(response.encoding or "utf-8", errors="replace"),
                )
    except JobImportError:
        raise
    except httpx.HTTPError as error:
        raise JobImportError("não foi possível acessar a fonte") from error

    raise JobImportError("a fonte não retornou um documento")


def sanitize_html(value: str) -> str:
    """Convert HTML to readable text while dropping executable element contents."""

    parser = _DocumentParser()
    parser.feed(value)
    parser.close()
    return normalize_text(" ".join(parser.text_parts), "content") if parser.text_parts else ""


def extract_document_fields(document: FetchedDocument) -> tuple[str, str, str]:
    """Extract conservative display fields and safe text from a fetched document."""

    parser = _DocumentParser()
    parser.feed(document.body)
    parser.close()
    safe_content = sanitize_html(document.body)
    title = normalize_text(" ".join(parser.title_parts), "title") if parser.title_parts else ""
    parsed_url = urlsplit(document.url)
    fallback_raw = parsed_url.path.rstrip("/").rsplit("/", maxsplit=1)[-1]
    fallback_title = normalize_text(fallback_raw, "title") if fallback_raw else ""
    title = title or fallback_title or "Vaga importada"
    company = parser.meta_values.get("og:site_name") or parser.meta_values.get("application-name")
    if not company:
        company = (parsed_url.hostname or "Fonte externa").split(".", maxsplit=1)[0]
    company = normalize_text(company.replace("-", " "), "company")
    return title, company, safe_content or title


class _DocumentParser(HTMLParser):
    """Small dependency-free parser used for both metadata and safe text."""

    _SKIPPED_TAGS = {"script", "style", "noscript", "template"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text_parts: list[str] = []
        self.title_parts: list[str] = []
        self.meta_values: dict[str, str] = {}
        self._skip_depth = 0
        self._title_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        folded_tag = tag.casefold()
        if folded_tag in self._SKIPPED_TAGS:
            self._skip_depth += 1
            return
        if folded_tag == "title":
            self._title_depth += 1
        if folded_tag == "meta" and self._skip_depth == 0:
            attributes = {key.casefold(): value or "" for key, value in attrs}
            key = attributes.get("property") or attributes.get("name")
            content = attributes.get("content")
            if key and content:
                self.meta_values[key.casefold()] = content

    def handle_endtag(self, tag: str) -> None:
        folded_tag = tag.casefold()
        if folded_tag in self._SKIPPED_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
        elif folded_tag == "title" and self._title_depth > 0:
            self._title_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        self.text_parts.append(data)
        if self._title_depth > 0:
            self.title_parts.append(data)
