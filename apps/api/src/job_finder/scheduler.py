"""Persistent scheduling primitives used by the local search runner."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from job_finder.source_models import (
    SearchRunRecord,
    SourceConfigRecord,
    due_sources,
    schedule_next_run,
    utc_now,
)


class PersistentScheduler:
    """Recover interrupted runs and calculate due work from persisted timestamps."""

    def recover_interrupted_runs(self, session: Session) -> int:
        """Mark runs left in-flight by a process shutdown as failed and retryable."""

        runs = list(
            session.scalars(
                select(SearchRunRecord).where(SearchRunRecord.status.in_(("pending", "running")))
            )
        )
        for run in runs:
            run.status = "failed"
            run.error_message = "Execução interrompida pelo encerramento da aplicação."
            run.finished_at = utc_now()
            source = session.get(SourceConfigRecord, run.source_config_id)
            if source is not None:
                schedule_next_run(source, run.finished_at)
        session.flush()
        return len(runs)

    def due(self, session: Session, now: datetime | None = None) -> list[SourceConfigRecord]:
        """Return sources whose persisted schedule is due now."""

        return due_sources(session, now)
