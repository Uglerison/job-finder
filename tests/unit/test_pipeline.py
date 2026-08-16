import pytest

from job_finder.pipeline import (
    InvalidTransitionError,
    MissingClosureReasonError,
    transition_status,
)


def test_pipeline_allows_expected_progression_and_rejects_invalid_moves() -> None:
    assert transition_status("found", "applied") == "transition"
    assert transition_status("applied", "interview") == "transition"
    with pytest.raises(InvalidTransitionError):
        transition_status("found", "hired")


def test_pipeline_allows_explicit_correction_as_an_auditable_event() -> None:
    assert transition_status("rejected", "pending", correction=True) == "correction"


def test_terminal_closure_requires_a_reason() -> None:
    with pytest.raises(MissingClosureReasonError, match="reason"):
        transition_status("found", "rejected")

    assert transition_status("found", "rejected", closure_reason="not_fit") == "transition"
