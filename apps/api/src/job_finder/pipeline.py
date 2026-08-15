"""Explicit, auditable transitions for the application pipeline."""

from typing import Literal

from sqlalchemy.orm import Session

from job_finder.applications import (
    Application,
    ApplicationStatus,
    ClosingReason,
    append_application_event,
)

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


class MissingClosureReasonError(ValueError):
    """Raised when a terminal outcome is recorded without an explanation."""


class InvalidClosureReasonError(ValueError):
    """Raised when a closure reason is used for a non-closable phase."""


CLOSURE_REQUIRED_STATUSES = {"rejected", "withdrawn", "expired"}
CLOSABLE_STATUSES = CLOSURE_REQUIRED_STATUSES | {"hired"}


def transition_status(
    current_status: str,
    target_status: str,
    *,
    correction: bool = False,
    closure_reason: ClosingReason | None = None,
) -> TransitionKind:
    """Validate a normal move or require an explicit correction marker."""

    if target_status == current_status:
        raise InvalidTransitionError("Target status must differ from the current status.")
    if target_status in CLOSURE_REQUIRED_STATUSES and closure_reason is None:
        raise MissingClosureReasonError(f"A closure reason is required for status {target_status}.")
    if closure_reason is not None and target_status not in CLOSABLE_STATUSES:
        raise InvalidClosureReasonError(
            f"A closure reason cannot be used for status {target_status}."
        )
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
    closure_reason: ClosingReason | None = None,
) -> tuple[Application, object]:
    """Validate and persist one state transition with its audit event."""

    kind = transition_status(
        application.current_status,
        target_status,
        correction=correction,
        closure_reason=closure_reason,
    )
    event_record = append_application_event(
        session,
        application,
        kind=kind,
        to_status=target_status,
        note=note,
        closure_reason=closure_reason,
    )
    return application, event_record
