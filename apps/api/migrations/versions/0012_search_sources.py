"""Add source configuration, search runs and duplicate review records.

Revision ID: 0012_search_sources
Revises: 0011_recoverable_trash
Create Date: 2026-08-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_search_sources"
down_revision: str | None = "0011_recoverable_trash"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create persistent source settings, run audit and duplicate review tables."""

    op.create_table(
        "source_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_key", sa.String(length=64), nullable=False, unique=True),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("endpoint", sa.String(length=2048), nullable=False),
        sa.Column("terms_url", sa.String(length=2048), nullable=True),
        sa.Column("data_format", sa.String(length=32), nullable=False, server_default="json"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("schedule_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("frequency_minutes", sa.Integer(), nullable=False, server_default="1440"),
        sa.Column("daily_limit", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("per_run_limit", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("secret_ref", sa.String(length=255), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("backoff_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_source_configs_next_run_at", "source_configs", ["next_run_at"])

    op.create_table(
        "search_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_config_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("query", sa.JSON(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("candidates_seen", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("jobs_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("exact_duplicates", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("approximate_duplicates", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("cancellation_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("current_cursor", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["source_config_id"], ["source_configs.id"]),
    )
    op.create_index("ix_search_runs_status", "search_runs", ["status"])
    op.create_index("ix_search_runs_requested_at", "search_runs", ["requested_at"])

    op.create_table(
        "duplicate_suggestions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("existing_job_id", sa.Integer(), nullable=False),
        sa.Column("source_key", sa.String(length=64), nullable=False),
        sa.Column("candidate", sa.JSON(), nullable=False),
        sa.Column("similarity", sa.Float(), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["existing_job_id"], ["jobs.id"]),
    )
    op.create_index("ix_duplicate_suggestions_status", "duplicate_suggestions", ["status"])


def downgrade() -> None:
    """Remove source search audit tables in dependency order."""

    op.drop_index("ix_duplicate_suggestions_status", table_name="duplicate_suggestions")
    op.drop_table("duplicate_suggestions")
    op.drop_index("ix_search_runs_requested_at", table_name="search_runs")
    op.drop_index("ix_search_runs_status", table_name="search_runs")
    op.drop_table("search_runs")
    op.drop_index("ix_source_configs_next_run_at", table_name="source_configs")
    op.drop_table("source_configs")
