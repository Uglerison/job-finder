import pytest
from pydantic import ValidationError

from job_finder.source_models import SourceConfigData


def test_source_config_defaults_keep_automation_off_and_validate_limits() -> None:
    source = SourceConfigData(
        source_key="example",
        display_name="Example",
        endpoint="https://example.com/feed",
    )

    assert source.enabled is True
    assert source.schedule_enabled is False
    assert source.frequency_minutes == 1440
    assert source.daily_limit == 50


@pytest.mark.parametrize(
    "payload",
    [
        {"endpoint": "http://localhost/feed"},
        {"endpoint": "file:///tmp/feed"},
        {"endpoint": "https://example.com/feed", "frequency_minutes": 5},
    ],
)
def test_source_config_rejects_unsafe_or_unbounded_values(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        SourceConfigData(
            source_key="example",
            display_name="Example",
            **payload,
        )
