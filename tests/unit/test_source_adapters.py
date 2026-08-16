from datetime import timezone

import httpx
import pytest

from job_finder.source_adapters import (
    ArbeitnowAdapter,
    CancellationToken,
    JobicyAdapter,
    RemoteOkAdapter,
    SafeHttpClient,
    SourceCancelledError,
    SourceRateLimitError,
    SourceSearchRequest,
)


@pytest.mark.anyio
async def test_adapters_normalize_three_fixture_shapes() -> None:
    responses = {
        "https://remoteok.test/api": httpx.Response(
            200,
            json=[
                {"legal": "metadata"},
                {
                    "id": 10,
                    "url": "https://remoteok.test/jobs/1?utm_source=x",
                    "position": " Backend  Engineer ",
                    "company": "Example Labs",
                    "location": "Remote",
                    "description": "<p>Python</p><script>bad()</script>",
                    "date": "2026-08-15T10:00:00Z",
                },
            ],
        ),
        "https://arbeitnow.test/api": httpx.Response(
            200,
            json={
                "data": [
                    {
                        "slug": "backend-1",
                        "url": "https://arbeitnow.test/backend-1",
                        "title": "Backend Engineer",
                        "company_name": "Example Labs",
                        "location": "São Paulo",
                        "description": "<p>FastAPI</p>",
                        "created_at": "2026-08-15T10:00:00Z",
                    },
                ],
            },
        ),
        "https://jobicy.test/api": httpx.Response(
            200,
            json={
                "jobs": [
                    {
                        "id": 2,
                        "url": "https://jobicy.test/jobs/2",
                        "jobTitle": "Data Engineer",
                        "companyName": "Data Co",
                        "jobGeo": "Brazil",
                        "jobDescription": "SQL and Python",
                        "pubDate": "2026-08-15T10:00:00+00:00",
                    },
                ],
            },
        ),
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        return responses[str(request.url)]

    client = SafeHttpClient(transport=httpx.MockTransport(handler), jitter=lambda: 0.0)
    remote = await RemoteOkAdapter("https://remoteok.test/api", client).search(
        SourceSearchRequest(limit=10),
    )
    arbeitnow = await ArbeitnowAdapter("https://arbeitnow.test/api", client).search(
        SourceSearchRequest(limit=10),
    )
    jobicy = await JobicyAdapter("https://jobicy.test/api", client).search(
        SourceSearchRequest(limit=10),
    )

    assert remote.candidates[0].title == "Backend Engineer"
    assert "bad" not in remote.candidates[0].description
    assert remote.candidates[0].published_at is not None
    assert remote.candidates[0].published_at.tzinfo == timezone.utc
    assert arbeitnow.candidates[0].external_id == "backend-1"
    assert jobicy.candidates[0].company == "Data Co"


@pytest.mark.anyio
async def test_http_client_retries_429_then_succeeds_and_honors_cancellation() -> None:
    attempts = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"retry-after": "0"})
        return httpx.Response(200, json={"ok": True})

    sleeps: list[float] = []

    async def no_wait(delay: float) -> None:
        sleeps.append(delay)

    client = SafeHttpClient(
        transport=httpx.MockTransport(handler),
        sleep=no_wait,
        jitter=lambda: 0.0,
    )
    assert await client.get_json("https://source.test/feed") == {"ok": True}
    assert attempts == 2
    assert sleeps == [0.0]

    token = CancellationToken(cancelled=True)
    with pytest.raises(SourceCancelledError):
        await client.get_json("https://source.test/feed", cancellation=token)


@pytest.mark.anyio
async def test_http_client_exposes_rate_limit_after_retry_budget() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"retry-after": "1"})

    async def no_wait(_delay: float) -> None:
        return None

    client = SafeHttpClient(
        transport=httpx.MockTransport(handler),
        sleep=no_wait,
        jitter=lambda: 0.0,
    )
    with pytest.raises(SourceRateLimitError) as error:
        await client.get_json("https://source.test/feed", max_attempts=1)
    assert error.value.retry_after == 1.0
    assert error.value.method == "GET"
    assert error.value.url == "https://source.test/feed"
    assert error.value.status_code == 429
