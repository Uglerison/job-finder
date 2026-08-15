"""Explicit, auditable transitions for the application pipeline."""

from typing import Literal

from sqlalchemy.orm import Session

from job_finder.applications import Application, ApplicationStatus, append_application_event

TransitionKind = Literal["transition", "correction"]

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "found": {"pending", "applied", "rejected", "withdrawn", "expired"},
    "pending": {"found", "applied", "rejected", "withdrawn", "expired"},
    "applied": {"interview", "rejected", "withdrawn", "expired"},
    "interview": {"offer", "rejected", "withdrawn", "applied"},
    "offer": {"hired", "rejected", "withdrawn"},
    "hired": set(),
    "rejected": set(),
    "withdrawn": set(),
    "expired": set(),
}


class InvalidTransitionError(ValueError):
    """Raised when a requested pipeline move is not allowed."""


def transition_status(
    current_status: str,
    target_status: str,
    *,
    correction: bool = False,
) -> TransitionKind:
    """Validate a normal move or require an explicit correction marker."""

    if target_status == current_status:
        raise InvalidTransitionError("Target status must differ from the current status.")
    if correction:
        return "correction"
    if target_status not in ALLOWED_TRANSITIONS.get(current_status, set()):
        raise InvalidTransitionError(
            f"Transition from {current_status} to {target_status} is not allowed."
        )
    return "transition"


def transition_application(
    session: Session,
    application: Application,
    target_status: ApplicationStatus,
    *,
    note: str | None = None,
    correction: bool = False,
) -> tuple[Application, object]:
    """Validate and persist one state transition with its audit event."""

    kind = transition_status(application.current_status, target_status, correction=correction)
    event_record = append_application_event(
        session,
        application,
        kind=kind,
        to_status=target_status,
        note=note,
    )
    return application, event_record
