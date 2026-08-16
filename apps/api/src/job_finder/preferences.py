"""Validated general preferences and their single-row local persistence."""

from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator
from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, Session, mapped_column

from job_finder.database import Base

Locale = Literal["pt-BR", "en-US"]
CurrencyCode = Annotated[str, StringConstraints(to_upper=True, pattern=r"^[A-Z]{3}$")]
_COMMON_WINDOWS_TIMEZONES = {
    "America/Los_Angeles",
    "America/New_York",
    "America/Sao_Paulo",
    "Asia/Tokyo",
    "Europe/Lisbon",
    "Europe/London",
    "UTC",
}


class PreferencesData(BaseModel):
    """Settings that affect formatting, money and local data retention."""

    model_config = ConfigDict(extra="forbid")

    locale: Locale = "pt-BR"
    currency: CurrencyCode = "BRL"
    timezone: str = "America/Sao_Paulo"
    retention_days: int = Field(default=365, ge=30, le=3650)

    @field_validator("timezone")
    @classmethod
    def timezone_must_exist(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            if value not in _COMMON_WINDOWS_TIMEZONES:
                raise ValueError("timezone must be a valid IANA timezone") from exc
        return value


DEFAULT_PREFERENCES = PreferencesData()


class PreferencesRecord(Base):
    """Persisted singleton row for the local application's preferences."""

    __tablename__ = "preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    locale: Mapped[str] = mapped_column(String(16), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


def get_saved_preferences(session: Session) -> PreferencesRecord | None:
    """Return the singleton preferences row when the user has saved one."""

    return session.get(PreferencesRecord, 1)


def save_preferences(session: Session, preferences: PreferencesData) -> PreferencesRecord:
    """Create or update the singleton preferences row transactionally."""

    record = get_saved_preferences(session)
    if record is None:
        record = PreferencesRecord(id=1)
        session.add(record)

    record.locale = preferences.locale
    record.currency = preferences.currency
    record.timezone = preferences.timezone
    record.retention_days = preferences.retention_days
    session.flush()
    return record


def preferences_from_record(record: PreferencesRecord) -> PreferencesData:
    """Validate persisted values before returning them through an API."""

    return PreferencesData.model_validate(
        {
            "locale": record.locale,
            "currency": record.currency,
            "timezone": record.timezone,
            "retention_days": record.retention_days,
        },
    )
