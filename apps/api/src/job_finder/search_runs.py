"""Execution coordinator for source searches, persistence and cancellation."""

import asyncio
from collections.abc import Callable
from datetime import datetime, timedelta
from time import monotonic

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from job_finder.source_adapters import (
    CancellationToken,
    SourceAdapterError,
    SourceCancelledError,
    SourceRateLimitError,
    SourceRegistry,
    SourceSearchRequest,
    SourceSearchResult,
)
from job_finder.source_dedup import DedupeKind, ingest_candidate
from job_finder.source_models import (
    SearchRunRecord,
    SourceConfigRecord,
    schedule_next_run,
    utc_now,
)


class SearchRunLimitError(RuntimeError):
    """Raised before a run when a source is disabled, backed off or over budget."""


def daily_run_count(session: Session, source_id: int, now: datetime | None = None) -> int:
    """Count started runs since UTC midnight for the source's daily budget."""

    current = now or utc_now()
    start = current.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(
        session.scalar(
            select(func.count(SearchRunRecord.id)).where(
                SearchRunRecord.source_config_id == source_id,
                SearchRunRecord.requested_at >= start,
                SearchRunRecord.status.in_(
                    ("running", "completed", "partial", "failed", "cancelled")
                ),
            ),
        )
        or 0
    )


def ensure_run_allowed(
    session: Session,
    source: SourceConfigRecord,
    now: datetime | None = None,
) -> None:
    """Apply enabled, backoff and daily run policies before network access."""

    current = now or utc_now()
    if not source.enabled:
        raise SearchRunLimitError("A fonte está pausada.")
    if source.backoff_until is not None and source.backoff_until > current:
        raise SearchRunLimitError(
            "A fonte está em pausa automática por limite ou erro transitório."
        )
    if daily_run_count(session, source.id, current) >= source.daily_limit:
        raise SearchRunLimitError("O limite diário desta fonte foi atingido.")


def mark_run_started(session: Session, run: SearchRunRecord) -> None:
    """Transition a pending run to running exactly once."""

    if run.status != "pending":
        return
    run.status = "running"
    run.started_at = utc_now()
    session.flush()


async def execute_search_run(
    session_factory: sessionmaker[Session],
    run_id: int,
    registry: SourceRegistry,
    token: CancellationToken,
    *,
    on_candidate: Callable[[int], None] | None = None,
) -> SearchRunRecord:
    """Run one adapter cooperatively and persist every outcome for diagnosis."""

    started_clock = monotonic()
    with session_factory() as session:
        run = session.get(SearchRunRecord, run_id)
        if run is None:
            raise SearchRunLimitError("Execução não encontrada.")
        source = session.get(SourceConfigRecord, run.source_config_id)
        if source is None:
            raise SearchRunLimitError("Fonte da execução não encontrada.")
        try:
            if run.cancellation_requested:
                run.status = "cancelled"
                run.error_message = "Busca cancelada pelo usuário."
                session.commit()
                return run
            ensure_run_allowed(session, source)
            mark_run_started(session, run)
            session.commit()
            adapter = registry.get(source.source_key, source.endpoint, source.timeout_seconds)
            request = SourceSearchRequest(
                query=_query_text(run.query, "query"),
                location=_query_text(run.query, "location"),
                limit=min(
                    source.per_run_limit,
                    _query_int(run.query, "limit", source.per_run_limit),
                ),
                cursor=_query_text(run.query, "cursor"),
                cancellation=token,
            )
            result = await adapter.search(request)
            token.raise_if_cancelled()
            _persist_candidates(session, run, result, token, on_candidate)
            run.current_cursor = result.next_cursor
            run.status = "partial" if result.partial or result.warnings else "completed"
            run.error_message = "; ".join(result.warnings) if result.warnings else None
            source.last_error = None
            source.consecutive_failures = 0
            source.backoff_until = None
        except SourceCancelledError as error:
            session.rollback()
            run = session.get(SearchRunRecord, run_id)
            if run is None:
                raise
            run.status = "cancelled"
            run.error_message = str(error)
        except SourceRateLimitError as error:
            session.rollback()
            run = session.get(SearchRunRecord, run_id)
            source = session.get(SourceConfigRecord, run.source_config_id) if run else None
            if run is None or source is None:
                raise
            run.status = "failed"
            run.error_message = str(error)
            source.last_error = str(error)
            source.consecutive_failures += 1
            delay = max(60.0, error.retry_after or min(3600.0, 2**source.consecutive_failures * 60))
            source.backoff_until = utc_now() + timedelta(seconds=delay)
        except (SourceAdapterError, SearchRunLimitError, ValueError) as error:
            session.rollback()
            run = session.get(SearchRunRecord, run_id)
            source = session.get(SourceConfigRecord, run.source_config_id) if run else None
            if run is None or source is None:
                raise
            run.status = "failed"
            run.error_message = str(error)
            source.consecutive_failures += 1
            source.last_error = str(error)
        finally:
            run = session.get(SearchRunRecord, run_id)
            source = session.get(SourceConfigRecord, run.source_config_id) if run else None
            if run is not None:
                finished = utc_now()
                run.finished_at = finished
                run.duration_ms = max(0, round((monotonic() - started_clock) * 1000))
                if run.status == "running":
                    run.status = "failed"
                    run.error_message = (
                        run.error_message or "A fonte encerrou sem resultado explícito."
                    )
                if source is not None:
                    source.last_run_at = finished
                    schedule_next_run(source, finished)
                session.commit()
    with session_factory() as final_session:
        final_run = final_session.get(SearchRunRecord, run_id)
        if final_run is None:
            raise SearchRunLimitError("Execução não finalizada.")
        return final_run


def _persist_candidates(
    session: Session,
    run: SearchRunRecord,
    result: SourceSearchResult,
    token: CancellationToken,
    on_candidate: Callable[[int], None] | None,
) -> None:
    for candidate in result.candidates:
        token.raise_if_cancelled()
        run.candidates_seen += 1
        dedupe_result = ingest_candidate(session, candidate)
        if dedupe_result.kind == DedupeKind.CREATED:
            run.jobs_created += 1
        elif dedupe_result.kind == DedupeKind.EXACT:
            run.exact_duplicates += 1
        else:
            run.approximate_duplicates += 1
        if on_candidate:
            on_candidate(run.candidates_seen)
        session.flush()


def _query_text(query: dict[str, object], key: str) -> str | None:
    value = query.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else None


def _query_int(query: dict[str, object], key: str, default: int) -> int:
    value = query.get(key)
    return value if isinstance(value, int) and value > 0 else default


class SearchTaskRegistry:
    """Keep in-process tasks and cancellation tokens for the local API instance."""

    def __init__(self) -> None:
        self.tasks: dict[int, asyncio.Task[SearchRunRecord]] = {}
        self.tokens: dict[int, CancellationToken] = {}

    def add(
        self,
        run_id: int,
        task: asyncio.Task[SearchRunRecord],
        token: CancellationToken,
    ) -> None:
        self.tasks[run_id] = task
        self.tokens[run_id] = token
        task.add_done_callback(lambda _task: self._remove(run_id))

    def cancel(self, run_id: int) -> bool:
        token = self.tokens.get(run_id)
        if token is None:
            return False
        token.cancel()
        return True

    def _remove(self, run_id: int) -> None:
        self.tasks.pop(run_id, None)
        self.tokens.pop(run_id, None)
