"""Create append-only history for AI analyses.

Revision ID: 0014_job_analysis_versions
Revises: 0013_ai_secrets
Create Date: 2026-08-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_job_analysis_versions"
down_revision: str | None = "0013_ai_secrets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create immutable provenance records for every explicit job re-analysis."""

    op.create_table(
        "job_analysis_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column(
            "job_content_version_id",
            sa.Integer(),
            sa.ForeignKey("job_content_versions.id"),
            nullable=False,
        ),
        sa.Column(
            "profile_version_id",
            sa.Integer(),
            sa.ForeignKey("profile_versions.id"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("prompt_version", sa.String(length=120), nullable=False),
        sa.Column("analysis", sa.JSON(), nullable=False),
        sa.Column("fit", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("job_id", "version_number"),
    )
    op.create_index(
        "ix_job_analysis_versions_job_id",
        "job_analysis_versions",
        ["job_id"],
    )


def downgrade() -> None:
    """Remove retained analysis history in reverse dependency order."""

    op.drop_index("ix_job_analysis_versions_job_id", table_name="job_analysis_versions")
    op.drop_table("job_analysis_versions")
