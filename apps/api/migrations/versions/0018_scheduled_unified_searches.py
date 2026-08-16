"""Persist unified searches, their executions and discovered job links."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_scheduled_unified_searches"
down_revision: str | None = "0017_provider_secrets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scheduled_searches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("query", sa.String(length=120), nullable=False),
        sa.Column("location", sa.String(length=120), nullable=True),
        sa.Column("work_model", sa.String(length=16), nullable=False, server_default="all"),
        sa.Column("limit", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("frequency_minutes", sa.Integer(), nullable=False, server_default="1440"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "profile_version_id",
            sa.Integer(),
            sa.ForeignKey("profile_versions.id"),
            nullable=True,
        ),
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
    op.create_index(
        "ix_scheduled_searches_due",
        "scheduled_searches",
        ["enabled", "next_run_at"],
    )
    op.create_table(
        "scheduled_search_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "scheduled_search_id",
            sa.Integer(),
            sa.ForeignKey("scheduled_searches.id"),
            nullable=False,
        ),
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
        sa.Column("provider_runs", sa.JSON(), nullable=False),
    )
    op.create_index(
        "ix_scheduled_search_runs_schedule_requested",
        "scheduled_search_runs",
        ["scheduled_search_id", "requested_at"],
    )
    op.create_table(
        "scheduled_search_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "run_id",
            sa.Integer(),
            sa.ForeignKey("scheduled_search_runs.id"),
            nullable=False,
        ),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id"), nullable=True),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("outcome", sa.String(length=20), nullable=False),
        sa.Column("candidate", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_scheduled_search_jobs_run_job",
        "scheduled_search_jobs",
        ["run_id", "job_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_scheduled_search_jobs_run_job", table_name="scheduled_search_jobs")
    op.drop_table("scheduled_search_jobs")
    op.drop_index(
        "ix_scheduled_search_runs_schedule_requested",
        table_name="scheduled_search_runs",
    )
    op.drop_table("scheduled_search_runs")
    op.drop_index("ix_scheduled_searches_due", table_name="scheduled_searches")
    op.drop_table("scheduled_searches")
