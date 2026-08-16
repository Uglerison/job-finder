"""Read-only usage metrics for the local dashboard."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from job_finder.ai_usage import UsageSummary, summarize_usage
from job_finder.job_analyses import JobAnalysisVersion

router = APIRouter(prefix="/api", tags=["ai-usage"])


def get_session(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        yield session


SessionDependency = Annotated[Session, Depends(get_session)]


@router.get("/ai/usage", response_model=UsageSummary)
def read_ai_usage(session: SessionDependency) -> UsageSummary:
    """Return counters only; prompts, API keys and job text never leave the backend."""

    return summarize_usage(record.usage or {} for record in session.query(JobAnalysisVersion))
