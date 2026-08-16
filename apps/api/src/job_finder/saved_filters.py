"""Persisted, validated filter presets shared by the inbox and dashboard."""

from datetime import datetime
from typing import cast

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import JSON, DateTime, Integer, String, UniqueConstraint, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from job_finder.database import Base

ALLOWED_FILTER_KEYS = frozenset({"q", "status", "source_key", "order", "from", "to", "timezone"})


class SavedFilterData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)
    query: dict[str, str | None] = Field(default_factory=dict, max_length=12)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: dict[str, str | None]) -> dict[str, str | None]:
        unknown = set(value) - ALLOWED_FILTER_KEYS
        if unknown:
            raise ValueError(f"Filtros não suportados: {', '.join(sorted(unknown))}.")
        return {key: item.strip() if isinstance(item, str) else None for key, item in value.items()}


class SavedFilterRecord(Base):
    __tablename__ = "saved_filters"
    __table_args__ = (UniqueConstraint("name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    query: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


def list_saved_filters(session: Session) -> list[SavedFilterRecord]:
    return list(session.scalars(select(SavedFilterRecord).order_by(SavedFilterRecord.name)))


def create_saved_filter(session: Session, payload: SavedFilterData) -> SavedFilterRecord:
    record = SavedFilterRecord(
        name=payload.name,
        query=cast(dict[str, object], payload.query),
    )
    session.add(record)
    session.flush()
    return record


def update_saved_filter(
    session: Session,
    record: SavedFilterRecord,
    payload: SavedFilterData,
) -> SavedFilterRecord:
    record.name = payload.name
    record.query = cast(dict[str, object], payload.query)
    session.flush()
    return record
