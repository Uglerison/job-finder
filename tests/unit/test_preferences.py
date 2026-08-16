import pytest
from pydantic import ValidationError

from job_finder.preferences import DEFAULT_PREFERENCES, PreferencesData


def test_preferences_have_local_defaults_and_accept_a_valid_timezone() -> None:
    assert DEFAULT_PREFERENCES.locale == "pt-BR"
    assert DEFAULT_PREFERENCES.currency == "BRL"
    assert DEFAULT_PREFERENCES.timezone == "America/Sao_Paulo"
    assert DEFAULT_PREFERENCES.retention_days == 365

    preferences = PreferencesData(
        locale="en-US",
        currency="USD",
        timezone="America/New_York",
        retention_days=90,
    )

    assert preferences.model_dump() == {
        "locale": "en-US",
        "currency": "USD",
        "timezone": "America/New_York",
        "retention_days": 90,
    }


@pytest.mark.parametrize("field, value", [("timezone", "Not/AZone"), ("retention_days", 2)])
def test_preferences_reject_invalid_values(field: str, value: object) -> None:
    payload = DEFAULT_PREFERENCES.model_dump()
    payload[field] = value

    with pytest.raises(ValidationError):
        PreferencesData.model_validate(payload)
