from datetime import datetime, timezone

from job_finder.normalization import RawJobData, normalize_job


def test_normalize_job_produces_stable_url_text_and_dates() -> None:
    normalized = normalize_job(
        RawJobData(
            canonical_url=(
                " HTTPS://Example.com:443/jobs//backend/?utm_source=newsletter&b=2&a=1#descricao "
            ),
            title="  Backend\n Engineer  ",
            company=" Example\t Labs ",
            location=" São   Paulo,   SP ",
            published_at=datetime(2026, 8, 15, 12, tzinfo=timezone.utc),
            expires_at=datetime(2026, 8, 30, 12, tzinfo=timezone.utc),
        ),
    )

    assert normalized.canonical_url == "https://example.com/jobs/backend?a=1&b=2"
    assert normalized.title == "Backend Engineer"
    assert normalized.company == "Example Labs"
    assert normalized.location == "São Paulo, SP"
    assert normalized.published_at == datetime(2026, 8, 15, 12, tzinfo=timezone.utc)
    assert normalized.expires_at == datetime(2026, 8, 30, 12, tzinfo=timezone.utc)


def test_normalize_job_rejects_non_http_urls_and_inverted_dates() -> None:
    invalid_url = RawJobData(
        canonical_url="javascript:alert(1)",
        title="Backend Engineer",
        company="Example Labs",
    )

    try:
        normalize_job(invalid_url)
    except ValueError as error:
        assert "http" in str(error)
    else:
        raise AssertionError("Expected non-HTTP URL to be rejected")

    inverted_dates = RawJobData(
        canonical_url="https://example.com/jobs/1",
        title="Backend Engineer",
        company="Example Labs",
        published_at=datetime(2026, 8, 30, tzinfo=timezone.utc),
        expires_at=datetime(2026, 8, 15, tzinfo=timezone.utc),
    )

    try:
        normalize_job(inverted_dates)
    except ValueError as error:
        assert "expires_at" in str(error)
    else:
        raise AssertionError("Expected inverted dates to be rejected")
