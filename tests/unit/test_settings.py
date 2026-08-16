from pathlib import Path

import pytest
from pydantic import ValidationError

from job_finder.settings import Settings, get_settings


@pytest.fixture(autouse=True)
def reset_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_settings_use_safe_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("JOB_FINDER_ENVIRONMENT", raising=False)
    monkeypatch.delenv("JOB_FINDER_LOG_LEVEL", raising=False)
    monkeypatch.delenv("JOB_FINDER_DATA_DIR", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    settings = Settings()

    assert settings.environment == "development"
    assert settings.log_level == "INFO"
    assert settings.data_dir == tmp_path / "JobFinder"
    assert settings.openai_api_key is None


def test_settings_can_be_overridden_by_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    custom_data_dir = tmp_path / "custom-data"
    monkeypatch.setenv("JOB_FINDER_ENVIRONMENT", "test")
    monkeypatch.setenv("JOB_FINDER_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("JOB_FINDER_DATA_DIR", str(custom_data_dir))

    settings = Settings()

    assert settings.environment == "test"
    assert settings.log_level == "DEBUG"
    assert settings.data_dir == custom_data_dir


def test_settings_reject_invalid_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JOB_FINDER_ENVIRONMENT", "staging")

    with pytest.raises(ValidationError):
        Settings()


def test_settings_do_not_reveal_api_key_in_representation() -> None:
    settings = Settings(openai_api_key="secret-value")

    assert "secret-value" not in repr(settings)


def test_get_settings_returns_a_cached_instance() -> None:
    assert get_settings() is get_settings()
