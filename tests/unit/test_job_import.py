import httpx
import pytest

from job_finder.job_import import (
    MAX_REDIRECTS,
    FetchedDocument,
    JobImportError,
    extract_document_fields,
    fetch_public_document,
    sanitize_html,
    validate_public_url,
)


def test_import_policy_rejects_local_private_and_non_http_destinations() -> None:
    for url in (
        "file:///C:/secret.txt",
        "http://localhost:8000/jobs/1",
        "http://127.0.0.1/jobs/1",
        "http://169.254.169.254/latest/meta-data",
        "http://10.0.0.5/jobs/1",
    ):
        with pytest.raises(ValueError):
            validate_public_url(url)

    assert validate_public_url("https://jobs.example.com/opportunities/1") == (
        "https://jobs.example.com/opportunities/1"
    )


def test_import_sanitizes_markup_and_extracts_stable_job_fields() -> None:
    document = FetchedDocument(
        url="https://jobs.example.com/opportunities/backend-1",
        content_type="text/html",
        body=(
            "<html><head><title>Backend Engineer | Example Labs</title>"
            '<meta property="og:site_name" content="Example Labs"></head>'
            "<body><h1>Backend Engineer</h1><script>alert(1)</script>"
            "<p>Trabalhe com Python &amp; FastAPI.</p></body></html>"
        ),
    )

    title, company, safe_content = extract_document_fields(document)

    assert title == "Backend Engineer | Example Labs"
    assert company == "Example Labs"
    assert "alert" not in safe_content
    assert "Trabalhe com Python & FastAPI." in safe_content
    assert "<script>" not in sanitize_html(document.body)


@pytest.mark.anyio
async def test_import_stops_after_the_redirect_limit(monkeypatch) -> None:
    calls: list[str] = []

    class RedirectResponse:
        status_code = 302
        headers = {"location": "/next"}
        content = b""

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args) -> None:
            return None

        async def get(self, url: str, *, follow_redirects: bool) -> RedirectResponse:
            assert follow_redirects is False
            calls.append(url)
            return RedirectResponse()

    monkeypatch.setattr(httpx, "AsyncClient", lambda **_kwargs: FakeClient())

    with pytest.raises(JobImportError, match="limite de redirecionamentos"):
        await fetch_public_document("https://jobs.example.com/first")

    assert len(calls) == MAX_REDIRECTS + 1
