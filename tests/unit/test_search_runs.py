from pathlib import Path

import pytest

from job_finder.database import create_database_engine, create_session_factory, run_migrations
from job_finder.search_runs import execute_search_run
from job_finder.source_adapters import (
    CancellationToken,
    SourceCandidate,
    SourceRateLimitError,
    SourceRegistry,
    SourceSearchResult,
)
from job_finder.source_models import SearchRunRecord, create_search_run, ensure_default_sources


class OneCandidateAdapter:
    source_key = "remoteok"

    async def search(self, request):
        request.cancellation.raise_if_cancelled()
        return SourceSearchResult(
            (
                SourceCandidate(
                    source_key=self.source_key,
                    external_id="1",
                    url="https://source.test/1",
                    title="Backend Engineer",
                    company="Example Labs",
                    location="Remote",
                    description="Python",
                ),
            )
        )


class RateLimitedAdapter:
    source_key = "remoteok"

    async def search(self, request):
        raise SourceRateLimitError("slow down", retry_after=60)


def _run(tmp_path: Path, adapter, token: CancellationToken):
    run_migrations(tmp_path)
    factory = create_session_factory(create_database_engine(tmp_path))
    with factory() as session:
        source = ensure_default_sources(session)[0]
        run = create_search_run(session, source, {"limit": 1})
        session.commit()
        registry = SourceRegistry({source.source_key: adapter})
        return factory, run.id, registry, token


@pytest.mark.anyio
async def test_cancelled_run_does_not_persist_candidates(tmp_path: Path) -> None:
    token = CancellationToken(cancelled=True)
    factory, run_id, registry, token = _run(tmp_path, OneCandidateAdapter(), token)

    result = await execute_search_run(factory, run_id, registry, token)

    assert result.status == "cancelled"
    with factory() as session:
        run = session.get(SearchRunRecord, run_id)
        assert run is not None
        assert run.candidates_seen == 0
        assert run.finished_at is not None


@pytest.mark.anyio
async def test_rate_limit_marks_run_failed_and_source_backed_off(tmp_path: Path) -> None:
    factory, run_id, registry, token = _run(tmp_path, RateLimitedAdapter(), CancellationToken())

    result = await execute_search_run(factory, run_id, registry, token)

    assert result.status == "failed"
    with factory() as session:
        run = session.get(SearchRunRecord, run_id)
        assert run is not None
        source = run.source
        assert source.backoff_until is not None
        assert source.consecutive_failures == 1
