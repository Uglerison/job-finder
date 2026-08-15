"""Create normalized jobs, source origins and immutable raw content versions.

Revision ID: 0004_jobs
Revises: 0003_preferences
Create Date: 2026-08-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_jobs"
down_revision: str | None = "0003_preferences"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create normalized job and source-evidence tables."""

    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("canonical_url", sa.String(length=2048), nullable=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("company", sa.String(length=240), nullable=False),
        sa.Column("location", sa.String(length=240), nullable=True),
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
        sa.UniqueConstraint("canonical_url", name="uq_jobs_canonical_url"),
    )

    op.create_table(
        "job_origins",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("url", sa.String(length=2048), nullable=True),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
        sa.UniqueConstraint("job_id", "source", "external_id"),
    )
    op.create_index("ix_job_origins_job_id", "job_origins", ["job_id"])

    op.create_table(
        "job_content_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("origin_id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("raw_content", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["origin_id"], ["job_origins.id"]),
        sa.UniqueConstraint("origin_id", "version_number"),
    )
    op.create_index(
        "ix_job_content_versions_origin_id",
        "job_content_versions",
        ["origin_id"],
    )


def downgrade() -> None:
    """Remove job content, origins and normalized jobs in dependency order."""

    op.drop_index("ix_job_content_versions_origin_id", table_name="job_content_versions")
    op.drop_table("job_content_versions")
    op.drop_index("ix_job_origins_job_id", table_name="job_origins")
    op.drop_table("job_origins")
    op.drop_table("jobs")
