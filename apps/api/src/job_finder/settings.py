"""Typed configuration for the local Job Finder backend."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "test", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def default_data_dir() -> Path:
    """Return the platform-appropriate folder for local application data."""

    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "JobFinder"

    return Path.home() / ".local" / "share" / "JobFinder"


class Settings(BaseSettings):
    """Runtime settings sourced from environment variables, never the frontend."""

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_prefix="JOB_FINDER_",
        extra="ignore",
    )

    environment: Environment = "development"
    log_level: LogLevel = "INFO"
    data_dir: Path = Field(default_factory=default_data_dir)
    openai_api_key: SecretStr | None = Field(default=None, repr=False)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return one immutable settings instance per process."""

    return Settings()
